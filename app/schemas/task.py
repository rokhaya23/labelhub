from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.task import TaskStatus

# Les tâches sont générées côté serveur quand une campagne
# passe à OPEN (répartition des items entre annotateurs assignés) 

class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    campaign_id: int
    item_id: int
    annotator_id: int
    status: TaskStatus
    created_at: datetime