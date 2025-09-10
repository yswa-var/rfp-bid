#!/usr/bin/env python3
"""
Team Integration and HITL (Human-in-the-Loop) Configuration
Handles integration with Dhruv's orchestration system and team workflows.
"""

import json
import asyncio
from datetime import datetime
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HITLEventType(Enum):
    """Types of HITL events that can be triggered."""
    DOCUMENT_QUALITY_CHECK = "document_quality_check"
    AMBIGUOUS_CONTENT_REVIEW = "ambiguous_content_review"
    EXTRACTION_VALIDATION = "extraction_validation"
    CHUNK_IMPROVEMENT_REVIEW = "chunk_improvement_review"
    FETCH_FAILURE_RESOLUTION = "fetch_failure_resolution"
    FINAL_OUTPUT_APPROVAL = "final_output_approval"

class Priority(Enum):
    """Priority levels for HITL events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class HITLEvent:
    """Represents a Human-in-the-Loop event requiring intervention."""
    event_id: str
    event_type: HITLEventType
    priority: Priority
    title: str
    description: str
    context: Dict[str, Any]
    timestamp: datetime
    assigned_to: Optional[str] = None
    status: str = "pending"
    response: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data['event_type'] = self.event_type.value
        data['priority'] = self.priority.value
        data['timestamp'] = self.timestamp.isoformat()
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HITLEvent':
        """Create from dictionary."""
        data['event_type'] = HITLEventType(data['event_type'])
        data['priority'] = Priority(data['priority'])
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

class TeamIntegration:
    """
    Handles integration with team workflows and HITL events.
    Designed to work with Dhruv's orchestration system.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self.hitl_handlers: Dict[HITLEventType, List[Callable]] = {}
        self.active_events: Dict[str, HITLEvent] = {}
        self.event_history: List[HITLEvent] = []
        
        # Team member assignments
        self.team_roles = {
            "arun": ["document_processing", "pdf_extraction", "quality_analysis"],
            "dhruv": ["orchestration", "workflow_management", "system_integration"],
            "team_lead": ["final_approval", "quality_assurance"]
        }
        
        # Initialize default handlers
        self._setup_default_handlers()
    
    def _setup_default_handlers(self):
        """Set up default HITL event handlers."""
        # Register default handlers for each event type
        self.register_hitl_handler(
            HITLEventType.DOCUMENT_QUALITY_CHECK, 
            self._default_quality_check_handler
        )
        self.register_hitl_handler(
            HITLEventType.AMBIGUOUS_CONTENT_REVIEW, 
            self._default_ambiguous_content_handler
        )
        self.register_hitl_handler(
            HITLEventType.EXTRACTION_VALIDATION, 
            self._default_extraction_validation_handler
        )
    
    def register_hitl_handler(
        self, 
        event_type: HITLEventType, 
        handler: Callable[[HITLEvent], Any]
    ):
        """Register a handler for a specific HITL event type."""
        if event_type not in self.hitl_handlers:
            self.hitl_handlers[event_type] = []
        self.hitl_handlers[event_type].append(handler)
        logger.info(f"Registered HITL handler for {event_type.value}")
    
    async def trigger_hitl_event(self, event: HITLEvent) -> HITLEvent:
        """
        Trigger a HITL event and handle it according to registered handlers.
        
        Args:
            event: The HITL event to trigger
            
        Returns:
            Updated event with response
        """
        logger.info(f"Triggering HITL event: {event.title}")
        
        # Assign to appropriate team member
        event.assigned_to = self._assign_event(event)
        
        # Store active event
        self.active_events[event.event_id] = event
        
        # Execute handlers
        if event.event_type in self.hitl_handlers:
            for handler in self.hitl_handlers[event.event_type]:
                try:
                    response = await self._call_handler_async(handler, event)
                    if response:
                        event.response = response
                        event.status = "completed"
                        break
                except Exception as e:
                    logger.error(f"Handler failed for {event.event_type}: {e}")
                    event.status = "error"
        
        # Move to history
        self.event_history.append(event)
        if event.event_id in self.active_events:
            del self.active_events[event.event_id]
        
        return event
    
    async def _call_handler_async(self, handler: Callable, event: HITLEvent) -> Any:
        """Call a handler, supporting both sync and async handlers."""
        if asyncio.iscoroutinefunction(handler):
            return await handler(event)
        else:
            return handler(event)
    
    def _assign_event(self, event: HITLEvent) -> str:
        """Assign event to appropriate team member based on type and roles."""
        event_type_str = event.event_type.value
        
        # Check team roles for assignment
        for member, responsibilities in self.team_roles.items():
            for responsibility in responsibilities:
                if responsibility in event_type_str or responsibility in event.title.lower():
                    return member
        
        # Default assignment based on event type
        assignment_map = {
            HITLEventType.DOCUMENT_QUALITY_CHECK: "arun",
            HITLEventType.AMBIGUOUS_CONTENT_REVIEW: "arun", 
            HITLEventType.EXTRACTION_VALIDATION: "arun",
            HITLEventType.CHUNK_IMPROVEMENT_REVIEW: "arun",
            HITLEventType.FETCH_FAILURE_RESOLUTION: "dhruv",
            HITLEventType.FINAL_OUTPUT_APPROVAL: "team_lead"
        }
        
        return assignment_map.get(event.event_type, "dhruv")
    
    # Default HITL event handlers
    async def _default_quality_check_handler(self, event: HITLEvent) -> Dict[str, Any]:
        """Default handler for document quality check events."""
        context = event.context
        quality_score = context.get("quality_score", 0.0)
        
        logger.info(f"Quality check for document: score={quality_score}")
        
        if quality_score < 0.5:
            return {
                "action": "reject",
                "reason": "Quality score too low",
                "recommendation": "Manual review required"
            }
        elif quality_score < 0.7:
            return {
                "action": "review",
                "reason": "Moderate quality score",
                "recommendation": "Consider improvement"
            }
        else:
            return {
                "action": "approve",
                "reason": "High quality score",
                "recommendation": "Proceed with processing"
            }
    
    async def _default_ambiguous_content_handler(self, event: HITLEvent) -> Dict[str, Any]:
        """Default handler for ambiguous content review."""
        context = event.context
        ambiguous_parts = context.get("ambiguous_parts", [])
        
        logger.info(f"Ambiguous content review: {len(ambiguous_parts)} parts")
        
        return {
            "action": "manual_review_required",
            "ambiguous_count": len(ambiguous_parts),
            "recommendation": "Human expert should review and clarify"
        }
    
    async def _default_extraction_validation_handler(self, event: HITLEvent) -> Dict[str, Any]:
        """Default handler for extraction validation."""
        context = event.context
        extracted_data = context.get("extracted_data", {})
        confidence = context.get("confidence", 0.0)
        
        logger.info(f"Extraction validation: confidence={confidence}")
        
        if confidence > 0.8:
            return {
                "action": "approve",
                "confidence": confidence,
                "recommendation": "Extraction approved"
            }
        else:
            return {
                "action": "review",
                "confidence": confidence,
                "recommendation": "Manual validation recommended"
            }
    
    # Integration with Dhruv's orchestration system
    def create_workflow_checkpoint(self, workflow_id: str, checkpoint_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a checkpoint for Dhruv's orchestration system.
        
        Args:
            workflow_id: Unique identifier for the workflow
            checkpoint_data: Data to store at this checkpoint
            
        Returns:
            Checkpoint information
        """
        checkpoint = {
            "workflow_id": workflow_id,
            "timestamp": datetime.now().isoformat(),
            "checkpoint_id": f"{workflow_id}_{int(datetime.now().timestamp())}",
            "data": checkpoint_data,
            "status": "active",
            "created_by": "arun_agent"
        }
        
        logger.info(f"Created workflow checkpoint: {checkpoint['checkpoint_id']}")
        return checkpoint
    
    def get_workflow_status(self, workflow_id: str) -> Dict[str, Any]:
        """Get current status of a workflow for orchestration."""
        # This would interface with Dhruv's system
        return {
            "workflow_id": workflow_id,
            "status": "in_progress",
            "active_events": len(self.active_events),
            "completed_events": len(self.event_history),
            "current_stage": "document_processing"
        }
    
    def notify_completion(self, workflow_id: str, results: Dict[str, Any]) -> Dict[str, Any]:
        """Notify orchestration system of task completion."""
        notification = {
            "workflow_id": workflow_id,
            "completion_time": datetime.now().isoformat(),
            "results": results,
            "events_processed": len(self.event_history),
            "status": "completed"
        }
        
        logger.info(f"Workflow completed: {workflow_id}")
        return notification

class AraunsTaskManager:
    """
    Specific task manager for Arun's responsibilities.
    Integrates with the broader team workflow.
    """
    
    def __init__(self, team_integration: TeamIntegration):
        self.team_integration = team_integration
        self.current_tasks: List[Dict[str, Any]] = []
        self.completed_tasks: List[Dict[str, Any]] = []
    
    async def handle_pdf_processing_task(
        self, 
        task_id: str, 
        pdf_sources: List[str],
        quality_threshold: float = 0.7
    ) -> Dict[str, Any]:
        """
        Handle a PDF processing task with HITL integration.
        
        Args:
            task_id: Unique task identifier
            pdf_sources: List of PDF URLs or paths
            quality_threshold: Minimum quality score threshold
            
        Returns:
            Task completion results
        """
        logger.info(f"Starting PDF processing task: {task_id}")
        
        task = {
            "task_id": task_id,
            "type": "pdf_processing",
            "sources": pdf_sources,
            "start_time": datetime.now().isoformat(),
            "status": "in_progress"
        }
        self.current_tasks.append(task)
        
        results = []
        hitl_events = []
        
        try:
            # Create workflow checkpoint
            checkpoint = self.team_integration.create_workflow_checkpoint(
                task_id, 
                {"stage": "pdf_processing_start", "sources": pdf_sources}
            )
            
            # Process each PDF source
            for i, source in enumerate(pdf_sources):
                try:
                    # Simulate fetch agent processing
                    # (In real implementation, this would call the FetchAgent)
                    
                    # Check if HITL event needed
                    if "complex" in source.lower() or "large" in source.lower():
                        event = HITLEvent(
                            event_id=f"{task_id}_review_{i}",
                            event_type=HITLEventType.DOCUMENT_QUALITY_CHECK,
                            priority=Priority.MEDIUM,
                            title=f"Complex document processing: {source}",
                            description=f"Document {source} may require special handling",
                            context={"source": source, "task_id": task_id},
                            timestamp=datetime.now()
                        )
                        
                        event_result = await self.team_integration.trigger_hitl_event(event)
                        hitl_events.append(event_result)
                        
                        if event_result.response and event_result.response.get("action") == "reject":
                            logger.warning(f"Document rejected: {source}")
                            continue
                    
                    # Simulate successful processing
                    result = {
                        "source": source,
                        "status": "success", 
                        "chunks_extracted": 15,
                        "quality_score": 0.8
                    }
                    results.append(result)
                    
                except Exception as e:
                    logger.error(f"Failed to process {source}: {e}")
                    
                    # Trigger HITL event for failure
                    failure_event = HITLEvent(
                        event_id=f"{task_id}_failure_{i}",
                        event_type=HITLEventType.FETCH_FAILURE_RESOLUTION,
                        priority=Priority.HIGH,
                        title=f"Processing failure: {source}",
                        description=f"Failed to process document: {e}",
                        context={"source": source, "error": str(e), "task_id": task_id},
                        timestamp=datetime.now()
                    )
                    
                    failure_result = await self.team_integration.trigger_hitl_event(failure_event)
                    hitl_events.append(failure_result)
            
            # Update task completion
            task["status"] = "completed"
            task["end_time"] = datetime.now().isoformat()
            task["results"] = results
            task["hitl_events"] = len(hitl_events)
            
            # Move to completed tasks
            self.current_tasks.remove(task)
            self.completed_tasks.append(task)
            
            # Notify team integration
            completion_data = {
                "task_id": task_id,
                "documents_processed": len(results),
                "hitl_interventions": len(hitl_events),
                "success_rate": len(results) / len(pdf_sources) if pdf_sources else 0
            }
            
            self.team_integration.notify_completion(task_id, completion_data)
            
            logger.info(f"PDF processing task completed: {task_id}")
            return completion_data
            
        except Exception as e:
            logger.error(f"Task failed: {task_id} - {e}")
            task["status"] = "failed"
            task["error"] = str(e)
            return {"task_id": task_id, "status": "failed", "error": str(e)}
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task."""
        # Check current tasks
        for task in self.current_tasks:
            if task["task_id"] == task_id:
                return task
        
        # Check completed tasks
        for task in self.completed_tasks:
            if task["task_id"] == task_id:
                return task
        
        return None
    
    def get_workload_summary(self) -> Dict[str, Any]:
        """Get summary of current workload for team coordination."""
        return {
            "active_tasks": len(self.current_tasks),
            "completed_tasks": len(self.completed_tasks),
            "current_task_ids": [t["task_id"] for t in self.current_tasks],
            "average_completion_time": self._calculate_average_completion_time(),
            "success_rate": self._calculate_success_rate()
        }
    
    def _calculate_average_completion_time(self) -> Optional[float]:
        """Calculate average task completion time in minutes."""
        if not self.completed_tasks:
            return None
        
        total_time = 0
        for task in self.completed_tasks:
            if "start_time" in task and "end_time" in task:
                start = datetime.fromisoformat(task["start_time"])
                end = datetime.fromisoformat(task["end_time"])
                total_time += (end - start).total_seconds() / 60
        
        return total_time / len(self.completed_tasks)
    
    def _calculate_success_rate(self) -> float:
        """Calculate task success rate."""
        if not self.completed_tasks:
            return 0.0
        
        successful = sum(1 for task in self.completed_tasks if task.get("status") == "completed")
        return successful / len(self.completed_tasks)

# Example usage and configuration
def create_team_config() -> Dict[str, Any]:
    """Create default team configuration."""
    return {
        "team_members": {
            "arun": {
                "role": "document_processor",
                "responsibilities": ["pdf_extraction", "quality_analysis", "chunk_processing"],
                "skills": ["python", "pdf_processing", "rag_systems"]
            },
            "dhruv": {
                "role": "orchestrator",
                "responsibilities": ["workflow_management", "system_integration", "coordination"],
                "skills": ["system_architecture", "workflow_design", "team_coordination"]
            }
        },
        "hitl_settings": {
            "auto_approve_threshold": 0.8,
            "manual_review_threshold": 0.5,
            "escalation_timeout": 1800  # 30 minutes
        },
        "integration_endpoints": {
            "orchestration_api": "http://localhost:8000/orchestration",
            "notification_webhook": "http://localhost:8000/notifications",
            "checkpoint_storage": "./checkpoints/"
        }
    }

if __name__ == "__main__":
    # Example usage
    async def main():
        # Initialize team integration
        config = create_team_config()
        team_integration = TeamIntegration(config)
        
        # Create Arun's task manager
        task_manager = AraunsTaskManager(team_integration)
        
        # Example PDF processing task
        pdf_sources = [
            "https://example.com/rfp-document.pdf",
            "https://example.com/complex-technical-spec.pdf"
        ]
        
        results = await task_manager.handle_pdf_processing_task(
            "task_001",
            pdf_sources
        )
        
        print(f"Task completed: {results}")
        print(f"Workload summary: {task_manager.get_workload_summary()}")
    
    # Run example
    asyncio.run(main())
