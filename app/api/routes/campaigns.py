from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.permissions import require_data_manager, require_reviewer, require_roles
from app.db.session import get_db
from app.models.annotation import AnnotationStatus
from app.models.role import RoleEnum
from app.models.user import User
from app.repositories.annotation_repository import annotation_repository
from app.repositories.campaign_repository import campaign_repository
from app.repositories.dataset_repository import dataset_repository
from app.repositories.user_repository import user_repository
from app.schemas.annotation import AnnotationResponse
from app.schemas.campaign import (
    CampaignAssignmentCreate,
    CampaignCreate,
    CampaignProgressResponse,
    CampaignResponse,
    CampaignReviewerCreate,
)

router = APIRouter()


def _get_owned_campaign_or_404(db: Session, campaign_id: int, current_user: User):
    campaign = campaign_repository.get_by_id(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campagne introuvable")
    if current_user.role != RoleEnum.ADMIN and campaign.created_by != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cette campagne ne vous appartient pas")
    return campaign


@router.post("", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_data_manager),
):
    dataset = dataset_repository.get_by_id(db, payload.dataset_id)
    if dataset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset introuvable")
    if dataset.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Ce dataset ne vous appartient pas")
    return campaign_repository.create(db, current_user.id, payload)


@router.post("/{campaign_id}/assignments", response_model=CampaignResponse)
def assign_annotators(
    campaign_id: int,
    payload: CampaignAssignmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    campaign = _get_owned_campaign_or_404(db, campaign_id, current_user)

    for annotator_id in payload.annotator_ids:
        annotator = user_repository.get_by_id(db, annotator_id)
        if annotator is None or annotator.role != RoleEnum.ANNOTATOR:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'utilisateur {annotator_id} n'est pas un annotateur valide",
            )

    campaign_repository.assign_annotators(db, campaign, payload.annotator_ids)
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/reviewers", response_model=CampaignResponse)
def assign_reviewers(
    campaign_id: int,
    payload: CampaignReviewerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    campaign = _get_owned_campaign_or_404(db, campaign_id, current_user)

    for reviewer_id in payload.reviewer_ids:
        reviewer = user_repository.get_by_id(db, reviewer_id)
        if reviewer is None or reviewer.role != RoleEnum.REVIEWER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"L'utilisateur {reviewer_id} n'est pas un reviewer valide",
            )

    campaign_repository.assign_reviewers(db, campaign, payload.reviewer_ids)
    db.refresh(campaign)
    return campaign


@router.patch("/{campaign_id}/open", response_model=CampaignResponse)
def open_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    campaign = _get_owned_campaign_or_404(db, campaign_id, current_user)
    return campaign_repository.open(db, campaign)


@router.patch("/{campaign_id}/close", response_model=CampaignResponse)
def close_campaign(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    campaign = _get_owned_campaign_or_404(db, campaign_id, current_user)
    return campaign_repository.close(db, campaign)


@router.get("/{campaign_id}/progress", response_model=CampaignProgressResponse)
def get_campaign_progress(
    campaign_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.DATA_MANAGER, RoleEnum.ADMIN)),
):
    campaign = _get_owned_campaign_or_404(db, campaign_id, current_user)
    return campaign_repository.progress(db, campaign)


@router.get("/{campaign_id}/annotations", response_model=list[AnnotationResponse])
def list_campaign_annotations(
    campaign_id: int,
    status_filter: AnnotationStatus | None = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_reviewer),
):
    """Permet au reviewer de voir les annotations de cette campagne avant de
    les valider - uniquement s'il est affecté à cette campagne précise via
    POST /campaigns/{id}/reviewers (sauf admin, qui voit tout).
    """
    campaign = campaign_repository.get_by_id(db, campaign_id)
    if campaign is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campagne introuvable")
    if current_user.role != RoleEnum.ADMIN and not campaign_repository.is_reviewer_assigned(
        db, campaign_id, current_user.id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Vous n'êtes pas affecté comme reviewer sur cette campagne"
        )
    return annotation_repository.list_for_campaign(
        db, campaign_id, status=status_filter, skip=skip, limit=limit
    )