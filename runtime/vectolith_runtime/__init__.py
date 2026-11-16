"""Vectolith model orchestration runtime."""
from .contracts import CONTRACT_VERSION, ModelRole, TaskRequest, TaskResult, TaskStatus
from .teacher_pipeline import (
    OpenAICompatibleTeacher, QualifiedTeacher, TeacherAssignmentPanel,
    TeacherEndpoint, TeacherQualification, TeachingTask,
    finalize_teacher_panel, generate_teaching_corpus, qualify_teacher, select_teacher_panel,
)
from .distillation_training import train_student
from .independent_evaluation import (
    EvaluationCase, evaluate_release, load_student_generator, leave_one_teacher_out,
    run_capability_suite, run_teacher_disabled_check,
)
from .distillation import (
    IndependenceEvidence, TeacherContribution, TeacherPanel, validate_panels,
)
from .engine import (
    ApprovalRequired, PermissionDenied, TaskRecord, TaskStore, ToolRegistry, VectolithRuntime,
)
from .loading import LoadedModel, ModelLoader, ModelLoaderRegistry, ModelRuntime
from .persistence import SQLiteModelRegistry
from .infrastructure_persistence import SQLiteInfrastructureRegistry
from .infrastructure_validation import validate_infrastructure_record
from .infrastructure import (
    INFRASTRUCTURE_CONTRACT_VERSION, AccessMode, ComputeAdapter, ComputeJob,
    ComputeRequest, ContributionClass, InfrastructureContribution,
    InfrastructureProvider, InfrastructureRegistry, MockComputeAdapter,
    ProviderState, QualificationState, TrainingAdapter, qualification_blockers,
)
from .registry import (
    CORE_PRIME_TARGET_CAPABILITIES, IDENTITY_CONTRACT_VERSION, FamilyIdentity, ModelLifecycle, ModelManifest, ModelRegistry,
)

__all__ = [
    "CONTRACT_VERSION", "ModelRole", "TaskRequest", "TaskResult", "TaskStatus",
    "ApprovalRequired", "PermissionDenied", "TaskRecord", "TaskStore",
    "ToolRegistry", "VectolithRuntime", "IDENTITY_CONTRACT_VERSION",
    "FamilyIdentity", "ModelLifecycle", "ModelManifest", "ModelRegistry",
    "SQLiteModelRegistry", "INFRASTRUCTURE_CONTRACT_VERSION", "AccessMode", "ComputeAdapter",
    "ComputeJob", "ComputeRequest", "ContributionClass", "InfrastructureContribution",
    "InfrastructureProvider", "InfrastructureRegistry", "SQLiteInfrastructureRegistry", "MockComputeAdapter",
    "ProviderState", "QualificationState", "TrainingAdapter", "qualification_blockers", "validate_infrastructure_record", "LoadedModel", "ModelLoader", "ModelLoaderRegistry", "ModelRuntime",
    "CORE_PRIME_TARGET_CAPABILITIES",
    "IndependenceEvidence", "TeacherContribution", "TeacherPanel", "validate_panels",
    "OpenAICompatibleTeacher", "QualifiedTeacher", "TeacherAssignmentPanel",
    "TeacherEndpoint", "TeacherQualification", "TeachingTask",
    "finalize_teacher_panel", "generate_teaching_corpus", "qualify_teacher", "select_teacher_panel",
    "train_student", "EvaluationCase", "evaluate_release", "load_student_generator", "leave_one_teacher_out",
    "run_capability_suite", "run_teacher_disabled_check",
]
