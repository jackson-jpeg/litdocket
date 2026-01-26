"""
Interactive Rule Template Generator

CLI tool to quickly create new jurisdiction rules without manually writing JSON.
Walks through rule creation step-by-step and generates properly formatted rule schema.

Usage:
    python -m scripts.generate_rule_template

Output:
    - Generates Python code for seed script
    - Can be copy-pasted directly into seed_comprehensive_rules.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from typing import List, Dict, Any
import json


class RuleTemplateGenerator:
    """Interactive CLI for generating rule templates."""

    def __init__(self):
        self.rule_data = {}
        self.deadlines = []

    def prompt(self, question: str, default: str = None, required: bool = True) -> str:
        """Prompt user for input with optional default."""
        default_text = f" [{default}]" if default else ""
        prompt_text = f"{question}{default_text}: "

        while True:
            response = input(prompt_text).strip()

            if not response and default:
                return default
            elif not response and required:
                print("❌ This field is required. Please enter a value.")
            elif not response and not required:
                return ""
            else:
                return response

    def prompt_select(self, question: str, options: List[str], default: str = None) -> str:
        """Prompt user to select from list of options."""
        print(f"\n{question}")
        for i, option in enumerate(options, 1):
            default_marker = " (default)" if option == default else ""
            print(f"  {i}. {option}{default_marker}")

        while True:
            response = input("Select number: ").strip()

            if not response and default:
                return default

            try:
                index = int(response) - 1
                if 0 <= index < len(options):
                    return options[index]
                else:
                    print(f"❌ Please enter a number between 1 and {len(options)}")
            except ValueError:
                print("❌ Please enter a valid number")

    def prompt_yes_no(self, question: str, default: bool = False) -> bool:
        """Prompt for yes/no answer."""
        default_text = "Y/n" if default else "y/N"
        response = input(f"{question} ({default_text}): ").strip().lower()

        if not response:
            return default
        return response in ['y', 'yes', 'true', '1']

    def gather_metadata(self):
        """Collect rule metadata."""
        print("\n" + "="*80)
        print("RULE METADATA")
        print("="*80)

        self.rule_data['name'] = self.prompt("Rule name (e.g., 'Answer to Complaint - Florida Civil')")
        self.rule_data['slug'] = self.prompt(
            "URL slug (lowercase-with-dashes)",
            default=self.rule_data['name'].lower().replace(' ', '-').replace(',', '')
        )
        self.rule_data['description'] = self.prompt("Short description")

        # Jurisdiction
        jurisdiction_type = self.prompt_select(
            "Jurisdiction type:",
            ["federal", "state", "local"],
            default="state"
        )
        self.rule_data['jurisdiction_type'] = jurisdiction_type

        if jurisdiction_type == "state":
            print("\n📍 State Abbreviations: CA, TX, NY, FL, IL, PA, OH, GA, NC, MI, etc.")
            state = self.prompt("State abbreviation (2 letters)").upper()
            self.rule_data['state'] = state
            self.rule_data['jurisdiction_code'] = f"{state.lower()}_civil"
        elif jurisdiction_type == "federal":
            self.rule_data['jurisdiction_code'] = "federal_civil"

        # Court level
        court_level = self.prompt_select(
            "Court level:",
            ["district", "superior", "circuit", "supreme", "appellate"],
            default="superior"
        )
        self.rule_data['court_level'] = court_level

        # Citations
        print("\n📚 Enter rule citations (one per line, empty line to finish):")
        citations = []
        while True:
            citation = input("  Citation: ").strip()
            if not citation:
                break
            citations.append(citation)
        self.rule_data['citations'] = citations

        # Tags
        print("\n🏷️  Enter tags (one per line, empty line to finish):")
        tags = []
        while True:
            tag = input("  Tag: ").strip()
            if not tag:
                break
            tags.append(tag)
        self.rule_data['tags'] = tags

    def gather_trigger_info(self):
        """Collect trigger information."""
        print("\n" + "="*80)
        print("TRIGGER CONFIGURATION")
        print("="*80)

        trigger_type = self.prompt_select(
            "Trigger type:",
            [
                "COMPLAINT_SERVED",
                "TRIAL_DATE",
                "MOTION_FILED",
                "JUDGMENT_ENTERED",
                "DISCOVERY_REQUEST",
                "DEPOSITION_NOTICED",
                "CASE_FILED"
            ],
            default="COMPLAINT_SERVED"
        )
        self.rule_data['trigger_type'] = trigger_type

        # Required fields
        print("\n📋 Required trigger fields:")
        print("   (These are inputs needed to execute the rule)")

        required_fields = []

        # Add default fields based on trigger type
        if trigger_type == "COMPLAINT_SERVED":
            required_fields.append({
                "name": "service_date",
                "type": "date",
                "label": "Date Complaint Was Served",
                "required": True
            })

            if self.prompt_yes_no("Include service method field?", default=True):
                required_fields.append({
                    "name": "service_method",
                    "type": "select",
                    "label": "Method of Service",
                    "options": ["personal", "mail", "substituted", "publication"],
                    "required": True,
                    "default": "personal"
                })

        elif trigger_type == "TRIAL_DATE":
            required_fields.append({
                "name": "trial_date",
                "type": "date",
                "label": "Trial Date",
                "required": True
            })

            if self.prompt_yes_no("Include trial type field?", default=True):
                required_fields.append({
                    "name": "trial_type",
                    "type": "select",
                    "label": "Trial Type",
                    "options": ["jury", "bench"],
                    "required": True,
                    "default": "jury"
                })

        self.rule_data['required_fields'] = required_fields

    def add_deadline(self):
        """Add a deadline to the rule."""
        print("\n" + "-"*80)
        print("ADD DEADLINE")
        print("-"*80)

        deadline = {}

        deadline['title'] = self.prompt("Deadline title (e.g., 'Answer Due')")
        deadline['id'] = self.prompt(
            "Deadline ID (lowercase_with_underscores)",
            default=deadline['title'].lower().replace(' ', '_').replace("'", "")
        )

        deadline['description'] = self.prompt("Description", required=False)

        # Offset
        offset_days = int(self.prompt("Offset days (number)", default="20"))
        deadline['offset_days'] = abs(offset_days)

        direction = self.prompt_select(
            "Before or after trigger?",
            ["after", "before"],
            default="after"
        )
        deadline['offset_direction'] = direction

        # If user entered negative number, assume "before"
        if offset_days < 0:
            deadline['offset_direction'] = "before"
            deadline['offset_days'] = abs(offset_days)

        # Priority
        priority = self.prompt_select(
            "Priority level:",
            ["FATAL", "CRITICAL", "IMPORTANT", "STANDARD", "INFORMATIONAL"],
            default="CRITICAL"
        )
        deadline['priority'] = priority

        # Rule citation
        deadline['applicable_rule'] = self.prompt("Rule citation", required=False)

        # Service days
        deadline['add_service_days'] = self.prompt_yes_no(
            "Add service method extension days?",
            default=False
        )

        # Party responsible
        party = self.prompt_select(
            "Party responsible:",
            ["plaintiff", "defendant", "both", "court"],
            default="defendant"
        )
        deadline['party_responsible'] = party

        # Calculation method
        calc_method = self.prompt_select(
            "Calculation method:",
            ["calendar_days", "business_days", "court_days"],
            default="calendar_days"
        )
        deadline['calculation_method'] = calc_method

        # Notes
        deadline['notes'] = self.prompt("Additional notes (optional)", required=False)

        self.deadlines.append(deadline)
        print(f"✅ Added deadline: {deadline['title']}")

    def generate_code(self) -> str:
        """Generate Python code for the rule."""
        function_name = f"create_{self.rule_data['slug'].replace('-', '_')}_rule"

        # Build rule schema
        rule_schema = {
            "metadata": {
                "name": self.rule_data['name'],
                "description": self.rule_data['description'],
                "effective_date": "2024-01-01",
                "citations": self.rule_data.get('citations', []),
                "jurisdiction_type": self.rule_data['jurisdiction_type']
            },
            "trigger": {
                "type": self.rule_data['trigger_type'],
                "required_fields": self.rule_data['required_fields']
            },
            "deadlines": self.deadlines,
            "dependencies": [],
            "validation": {
                "min_deadlines": 1,
                "max_deadlines": 10,
                "require_citations": True
            },
            "settings": {
                "auto_cascade_updates": True,
                "allow_manual_override": True,
                "notification_lead_days": [1, 3, 7, 14]
            }
        }

        if self.rule_data['jurisdiction_type'] == "state":
            rule_schema['metadata']['state'] = self.rule_data['state']

        rule_schema['metadata']['court_level'] = self.rule_data['court_level']

        # Generate Python code
        code = f'''
def {function_name}(db: Session, user_id: str) -> RuleTemplate:
    """
    {self.rule_data['name']}
    {', '.join(self.rule_data.get('citations', []))}
    """
    rule_schema = {json.dumps(rule_schema, indent=4)}

    template_id = str(uuid.uuid4())
    version_id = str(uuid.uuid4())

    rule_template = RuleTemplate(
        id=template_id,
        rule_name="{self.rule_data['name']}",
        slug="{self.rule_data['slug']}",
        jurisdiction="{self.rule_data['jurisdiction_code']}",
        trigger_type="{self.rule_data['trigger_type']}",
        created_by=user_id,
        is_public=True,
        is_official=True,
        current_version_id=version_id,
        version_count=1,
        status="active",
        description="{self.rule_data['description']}",
        tags={json.dumps(self.rule_data.get('tags', []))},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        published_at=datetime.utcnow()
    )

    rule_version = RuleVersion(
        id=version_id,
        rule_template_id=template_id,
        version_number=1,
        version_name="Initial Version",
        rule_schema=rule_schema,
        created_by=user_id,
        change_summary="Initial rule creation",
        is_validated=True,
        status="active",
        created_at=datetime.utcnow(),
        activated_at=datetime.utcnow()
    )

    db.add(rule_template)
    db.add(rule_version)
    db.commit()
    db.refresh(rule_template)

    return rule_template
'''

        return code

    def run(self):
        """Run the interactive generator."""
        print("\n" + "="*80)
        print("🎯 LITDOCKET RULE TEMPLATE GENERATOR")
        print("="*80)
        print("\nThis tool will help you create a new jurisdiction rule.")
        print("Follow the prompts to build your rule step-by-step.\n")

        # Gather information
        self.gather_metadata()
        self.gather_trigger_info()

        # Add deadlines
        print("\n" + "="*80)
        print("DEADLINES")
        print("="*80)

        while True:
            self.add_deadline()

            if not self.prompt_yes_no("\nAdd another deadline?", default=True):
                break

        # Generate code
        print("\n" + "="*80)
        print("GENERATED CODE")
        print("="*80)

        code = self.generate_code()

        print("\n📋 Copy and paste this into seed_comprehensive_rules.py:\n")
        print(code)

        # Save to file
        output_file = Path(__file__).parent / "generated_rule.py"
        with open(output_file, 'w') as f:
            f.write(code)

        print(f"\n✅ Code also saved to: {output_file}")
        print("\n🎉 Rule template generation complete!")
        print("\nNext steps:")
        print("  1. Review the generated code")
        print("  2. Copy into seed_comprehensive_rules.py")
        print("  3. Add function call to main()")
        print("  4. Test with: python -m scripts.seed_comprehensive_rules")


def main():
    """Run the generator."""
    generator = RuleTemplateGenerator()

    try:
        generator.run()
    except KeyboardInterrupt:
        print("\n\n❌ Generation cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
