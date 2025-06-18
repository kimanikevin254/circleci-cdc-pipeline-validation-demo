"""Main execution script"""

import json
from config import POSTGRES_CONFIG, S3_CONFIG, TABLE_CONFIGS
from cdc_pipeline_validator import CDCPipelineValidator

def main():
    # Initialize validator
    validator = CDCPipelineValidator(POSTGRES_CONFIG, S3_CONFIG, TABLE_CONFIGS)

    try:
        # Run baseline validation
        validator.run_baseline_validation()

        # Run change validation tests for each table
        for table_name in validator.table_configs.keys():
            print(f"\n--- Running change validation tests for table: {table_name} ---")

            # Generate test changes
            test_changes = validator.generate_test_changes(table_name)

            if test_changes:
                print(f"Running change validation test for {table_name}...")
                print(f"Generated data: {json.dumps(test_changes, indent=2)}")
                validator.run_change_validation_test(table_name, test_changes)
            else:
                print(f"No test changes generated for {table_name}. Skipping change validation.")

        # Generate and save report
        print("\nGenerating final report...")
        filename = validator.save_report()
        print(f"Report saved to {filename}")

    finally:
        validator.cleanup()


if __name__ == "__main__":
    main()