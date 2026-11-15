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
from .registry import (
    IDENTITY_CONTRACT_VERSION, FamilyIdentity, ModelLifecycle, ModelManifest, ModelRegistry,
)

__all__ = [
    "CONTRACT_VERSION", "ModelRole", "TaskRequest", "TaskResult", "TaskStatus",
    "ApprovalRequired", "PermissionDenied", "TaskRecord", "TaskStore",
    "ToolRegistry", "VectolithRuntime", "IDENTITY_CONTRACT_VERSION",
    "FamilyIdentity", "ModelLifecycle", "ModelManifest", "ModelRegistry",
    "IndependenceEvidence", "TeacherContribution", "TeacherPanel", "validate_panels",
    "OpenAICompatibleTeacher", "QualifiedTeacher", "TeacherAssignmentPanel",
    "TeacherEndpoint", "TeacherQualification", "TeachingTask",
    "finalize_teacher_panel", "generate_teaching_corpus", "qualify_teacher", "select_teacher_panel",
    "train_student", "EvaluationCase", "evaluate_release", "load_student_generator", "leave_one_teacher_out",
    "run_capability_suite", "run_teacher_disabled_check",
]
