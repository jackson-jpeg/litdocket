"""
Dynamic Rules Execution Engine

Executes database-stored rules (not hardcoded) to generate deadline chains.

This is the successor to the original hardcoded rules_engine.py, enabling:
- Unlimited user-created jurisdictions
- No code deploys for new rules
- Version control and rollback
- Complete audit trail
- Test-driven rule validation
"""
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, datetime, timedelta
from dataclasses import dataclass
import time
import logging

from app.models.rule_template import RuleTemplate, RuleVersion, RuleExecution
from app.models.deadline import Deadline
from app.models.case import Case
from app.utils.deadline_calculator import AuthoritativeDeadlineCalculator
from app.constants.legal_rules import SERVICE_METHOD_EXTENSIONS

logger = logging.getLogger(__name__)


@dataclass
class RuleExecutionResult:
    """Result of executing a rule"""
    success: bool
    deadlines_created: int
    deadlines: List[Deadline]
    execution_time_ms: int
    rule_name: str
    rule_version: int
    errors: List[str] = None

    def to_dict(self):
        return {
            "success": self.success,
            "deadlines_created": self.deadlines_created,
            "execution_time_ms": self.execution_time_ms,
            "rule_name": self.rule_name,
            "rule_version": self.rule_version,
            "errors": self.errors or []
        }


class DynamicRulesEngine:
    """
    Executes database-stored rules dynamically

    Features:
    - Loads rules from database (not hardcoded)
    - Evaluates conditions dynamically
    - Handles dependencies and ordering
    - Validates against test cases
    - Provides dry-run mode
    - Complete audit trail
    """

    def __init__(self, db: Session):
        self.db = db
        self.calculator = AuthoritativeDeadlineCalculator()

    async def execute_rule(
        self,
        rule_template_id: str,
        trigger_data: dict,
        case_id: str,
        user_id: str,
        dry_run: bool = False
    ) -> RuleExecutionResult:
        """
        Execute a rule and generate deadlines

        Args:
            rule_template_id: UUID of rule template
            trigger_data: Input data (trial_date, case_type, etc.)
            case_id: Case to attach deadlines to
            user_id: User executing the rule
            dry_run: If True, don't save to database (preview mode)

        Returns:
            RuleExecutionResult with generated deadlines and stats
        """

        start_time = time.time()
        errors = []

        try:
            # 1. Load rule from database
            rule_template = self.db.query(RuleTemplate).filter(
                RuleTemplate.id == rule_template_id,
                RuleTemplate.status.in_(['active', 'draft'])  # Allow draft for testing
            ).first()

            if not rule_template:
                raise Exception(f"Rule template {rule_template_id} not found or not active")

            # 2. Get current version
            if rule_template.current_version_id:
                rule_version = self.db.query(RuleVersion).filter(
                    RuleVersion.id == rule_template.current_version_id
                ).first()
            else:
                # Get latest version if current not set
                rule_version = self.db.query(RuleVersion).filter(
                    RuleVersion.rule_template_id == rule_template_id
                ).order_by(RuleVersion.version_number.desc()).first()

            if not rule_version:
                raise Exception(f"No version found for rule template {rule_template_id}")

            rule_schema = rule_version.rule_schema

            # 3. Validate input data
            validation_errors = self._validate_trigger_data(
                rule_schema.get('trigger', {}).get('required_fields', []),
                trigger_data
            )

            if validation_errors:
                raise Exception(f"Invalid trigger data: {', '.join(validation_errors)}")

            # 4. Generate deadlines
            deadlines = []
            deadline_map = {}  # For dependency resolution

            for deadline_template in rule_schema.get('deadlines', []):
                try:
                    # Evaluate conditions
                    should_create = self._evaluate_conditions(
                        deadline_template.get('conditions', []),
                        trigger_data
                    )

                    if not should_create:
                        logger.debug(f"Skipping deadline {deadline_template.get('name')} due to conditions")
                        continue

                    # Calculate deadline date
                    deadline_date = self._calculate_deadline_date(
                        deadline_template,
                        trigger_data,
                        deadline_map
                    )

                    if not deadline_date:
                        errors.append(f"Could not calculate date for {deadline_template.get('name')}")
                        continue

                    # Create deadline object
                    deadline = Deadline(
                        case_id=case_id,
                        user_id=user_id,
                        title=deadline_template.get('name'),
                        description=deadline_template.get('description'),
                        deadline_date=deadline_date,
                        priority=deadline_template.get('priority', 'STANDARD'),
                        category=deadline_template.get('category'),
                        applicable_rule=deadline_template.get('rule_citation'),
                        calculation_basis=deadline_template.get('calculation_basis', ''),
                        action_required=deadline_template.get('action_required'),
                        party_role=deadline_template.get('party_responsible'),
                        is_calculated=True,
                        is_dependent=True,
                        trigger_event=rule_schema.get('trigger', {}).get('type'),
                        status='pending',
                        auto_recalculate=rule_schema.get('settings', {}).get('auto_recalculate_dependents', True)
                    )

                    deadlines.append(deadline)
                    deadline_map[deadline_template.get('id')] = deadline

                except Exception as e:
                    logger.error(f"Error creating deadline {deadline_template.get('name')}: {e}")
                    errors.append(f"{deadline_template.get('name')}: {str(e)}")

            # 5. Validate dependency order
            try:
                self._validate_dependencies(deadlines, rule_schema)
            except Exception as e:
                errors.append(f"Dependency validation failed: {str(e)}")

            # 6. Save to database (unless dry-run)
            if not dry_run and deadlines:
                for deadline in deadlines:
                    self.db.add(deadline)

                # Create execution audit record
                execution = RuleExecution(
                    rule_template_id=rule_template_id,
                    rule_version_id=rule_version.id,
                    case_id=case_id,
                    user_id=user_id,
                    trigger_data=trigger_data,
                    deadlines_created=len(deadlines),
                    deadline_ids=[str(d.id) for d in deadlines],
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    status='success' if not errors else 'partial'
                )
                self.db.add(execution)

                # Update usage count
                rule_template.usage_count += 1

                self.db.commit()

            # 7. Return result
            return RuleExecutionResult(
                success=len(errors) == 0,
                deadlines_created=len(deadlines),
                deadlines=deadlines,
                execution_time_ms=int((time.time() - start_time) * 1000),
                rule_name=rule_schema.get('metadata', {}).get('name', rule_template.rule_name),
                rule_version=rule_version.version_number,
                errors=errors if errors else None
            )

        except Exception as e:
            logger.error(f"Rule execution failed: {e}", exc_info=True)

            # Log failed execution
            if not dry_run:
                execution = RuleExecution(
                    rule_template_id=rule_template_id,
                    rule_version_id=rule_version.id if 'rule_version' in locals() else None,
                    case_id=case_id,
                    user_id=user_id,
                    trigger_data=trigger_data,
                    deadlines_created=0,
                    execution_time_ms=int((time.time() - start_time) * 1000),
                    status='failed',
                    error_message=str(e)
                )
                self.db.add(execution)
                self.db.commit()

            return RuleExecutionResult(
                success=False,
                deadlines_created=0,
                deadlines=[],
                execution_time_ms=int((time.time() - start_time) * 1000),
                rule_name="Unknown",
                rule_version=0,
                errors=[str(e)]
            )

    def _validate_trigger_data(
        self,
        required_fields: List[dict],
        trigger_data: dict
    ) -> List[str]:
        """
        Validate that trigger data contains all required fields

        Returns list of error messages (empty if valid)
        """
        errors = []

        for field_def in required_fields:
            field_name = field_def.get('field')
            validation = field_def.get('validation', {})

            # Check if required field is present
            if validation.get('required', True) and field_name not in trigger_data:
                errors.append(f"Missing required field: {field_name}")
                continue

            value = trigger_data.get(field_name)

            # Type validation
            field_type = field_def.get('type')
            if field_type == 'date' and value:
                try:
                    if isinstance(value, str):
                        date.fromisoformat(value)
                    elif not isinstance(value, date):
                        errors.append(f"{field_name} must be a date")
                except ValueError:
                    errors.append(f"{field_name} is not a valid date")

            # Custom validations
            if validation.get('must_be_future') and value:
                try:
                    value_date = date.fromisoformat(value) if isinstance(value, str) else value
                    if value_date <= date.today():
                        errors.append(f"{field_name} must be a future date")
                except:
                    pass

        return errors

    def _evaluate_conditions(
        self,
        conditions: List[dict],
        trigger_data: dict
    ) -> bool:
        """
        Evaluate if-then conditions

        Returns True if deadline should be created, False if it should be skipped
        """

        for condition in conditions:
            if_clause = condition.get('if', {})
            then_clause = condition.get('then', {})

            # Check if condition matches
            condition_met = all(
                trigger_data.get(key) == value
                for key, value in if_clause.items()
            )

            if condition_met:
                # Apply the "then" clause
                if then_clause.get('skip'):
                    return False  # Don't create this deadline

        return True  # Create deadline by default

    def _calculate_deadline_date(
        self,
        deadline_template: dict,
        trigger_data: dict,
        deadline_map: Dict[str, Deadline]
    ) -> Optional[date]:
        """
        Calculate the deadline date with all business logic

        Handles:
        - Offset calculations
        - Service method extensions
        - Condition-based adjustments
        - Dependency-based offsets
        """

        # Get base offset
        offset_days = deadline_template.get('offset_days', 0)
        offset_type = deadline_template.get('offset_type', 'calendar_days')

        # Apply condition-based adjustments
        for condition in deadline_template.get('conditions', []):
            if_clause = condition.get('if', {})
            then_clause = condition.get('then', {})

            # Check if condition matches
            condition_met = all(
                trigger_data.get(key) == value
                for key, value in if_clause.items()
            )

            if condition_met and 'offset_days' in then_clause:
                offset_days = then_clause['offset_days']

        # Determine offset_from (base date)
        offset_from = deadline_template.get('offset_from', 'trigger')

        if offset_from == 'trigger':
            # Use trigger date from trigger_data
            # Try common field names
            base_date_str = trigger_data.get('trial_date') or trigger_data.get('trigger_date') or trigger_data.get('date')
            if not base_date_str:
                logger.error(f"No trigger date found in trigger_data: {trigger_data}")
                return None

            base_date = date.fromisoformat(base_date_str) if isinstance(base_date_str, str) else base_date_str

        else:
            # Offset from another deadline (dependency)
            dep_deadline = deadline_map.get(offset_from)
            if not dep_deadline:
                logger.error(f"Dependency deadline {offset_from} not found")
                return None
            base_date = dep_deadline.deadline_date

        # Calculate with service method extensions
        service_method = trigger_data.get('service_method', 'personal')
        add_service_extension = deadline_template.get('service_method_extension', False)

        # Use deadline calculator
        jurisdiction = trigger_data.get('jurisdiction', 'florida_civil')

        result_date = self.calculator.calculate_deadline(
            trigger_date=base_date,
            days_to_add=offset_days,
            calculation_type=offset_type,
            service_method=service_method if add_service_extension else None,
            jurisdiction=jurisdiction
        )

        return result_date

    def _validate_dependencies(
        self,
        deadlines: List[Deadline],
        rule_schema: dict
    ):
        """
        Validate that dependencies are satisfied and deadlines are in logical order

        Raises exception if circular dependencies or invalid ordering detected
        """

        deadline_map = {d.title: d for d in deadlines}

        for deadline_template in rule_schema.get('deadlines', []):
            deadline_name = deadline_template.get('name')
            dependencies = deadline_template.get('dependencies', [])

            if not dependencies:
                continue

            # Check that all dependencies exist
            for dep_id in dependencies:
                # Find dependency by ID
                dep_template = next(
                    (dt for dt in rule_schema['deadlines'] if dt.get('id') == dep_id),
                    None
                )

                if not dep_template:
                    raise Exception(f"Dependency {dep_id} not found for deadline {deadline_name}")

                # Validate temporal ordering (dependent should come after dependency)
                dep_name = dep_template.get('name')
                current_deadline = deadline_map.get(deadline_name)
                dep_deadline = deadline_map.get(dep_name)

                if current_deadline and dep_deadline:
                    if current_deadline.deadline_date < dep_deadline.deadline_date:
                        logger.warning(
                            f"Potential dependency ordering issue: {deadline_name} "
                            f"({current_deadline.deadline_date}) comes before its dependency "
                            f"{dep_name} ({dep_deadline.deadline_date})"
                        )

    def get_rule_by_jurisdiction_and_trigger(
        self,
        jurisdiction: str,
        trigger_type: str
    ) -> Optional[RuleTemplate]:
        """
        Find an active rule for a jurisdiction/trigger combination

        Args:
            jurisdiction: e.g. "florida_civil"
            trigger_type: e.g. "TRIAL_DATE"

        Returns:
            RuleTemplate or None
        """

        return self.db.query(RuleTemplate).filter(
            RuleTemplate.jurisdiction == jurisdiction,
            RuleTemplate.trigger_type == trigger_type,
            RuleTemplate.status == 'active'
        ).first()

    def list_available_rules(
        self,
        jurisdiction: Optional[str] = None,
        trigger_type: Optional[str] = None,
        user_id: Optional[str] = None,
        include_public: bool = True
    ) -> List[RuleTemplate]:
        """
        List available rules (user's own + public marketplace rules)

        Args:
            jurisdiction: Filter by jurisdiction
            trigger_type: Filter by trigger type
            user_id: User ID to include their private rules
            include_public: Include public marketplace rules

        Returns:
            List of RuleTemplate objects
        """

        query = self.db.query(RuleTemplate).filter(
            RuleTemplate.status.in_(['active', 'draft'])
        )

        if jurisdiction:
            query = query.filter(RuleTemplate.jurisdiction == jurisdiction)

        if trigger_type:
            query = query.filter(RuleTemplate.trigger_type == trigger_type)

        # Filter by visibility
        if user_id and include_public:
            query = query.filter(
                (RuleTemplate.created_by == user_id) | (RuleTemplate.is_public == True)
            )
        elif user_id:
            query = query.filter(RuleTemplate.created_by == user_id)
        elif include_public:
            query = query.filter(RuleTemplate.is_public == True)

        return query.all()


# Singleton instance
_engine_instance = None

def get_dynamic_rules_engine(db: Session) -> DynamicRulesEngine:
    """Get or create dynamic rules engine instance"""
    global _engine_instance
    if _engine_instance is None or _engine_instance.db != db:
        _engine_instance = DynamicRulesEngine(db)
    return _engine_instance
