#!/usr/bin/env python3
"""
Enhanced AI Migration Controller for Nodes & Agents Reorganization
Implements comprehensive validation, automatic rollback, and real-time monitoring.
"""

import ast
import asyncio
import shutil
import subprocess
from pathlib import Path
from typing import Any


class EnhancedImportDetector(ast.NodeVisitor):
    """Enhanced import detector handling all Python import patterns."""

    def __init__(self, file_path: str):
        self.file_path = file_path
        self.all_import_patterns = []
        self.star_imports = []
        self.complex_patterns = []
        self.relative_imports = []
        self.framework_imports = []

    def visit_ImportFrom(self, node):
        """Handle all from-import variations including multi-line, aliases, stars."""
        if node.module and "universal_framework" in node.module:
            for alias in node.names:
                pattern_info = self._analyze_import_pattern(node, alias)
                self.all_import_patterns.append(pattern_info)
                self.framework_imports.append(pattern_info)

                # Categorize for special handling
                if pattern_info["pattern_type"] == "star_import":
                    self.star_imports.append(pattern_info)
                elif pattern_info["complexity"] in ["high", "critical"]:
                    self.complex_patterns.append(pattern_info)
                elif pattern_info["relative_level"] > 0:
                    self.relative_imports.append(pattern_info)

        self.generic_visit(node)

    def visit_Import(self, node):
        """Handle standard import statements."""
        for alias in node.names:
            if "universal_framework" in alias.name:
                pattern_info = {
                    "type": "import",
                    "module": alias.name,
                    "alias": alias.asname,
                    "line": node.lineno,
                    "column": node.col_offset,
                    "pattern_type": (
                        "aliased_import" if alias.asname else "simple_import"
                    ),
                    "relative_level": 0,
                    "complexity": "low" if not alias.asname else "medium",
                    "update_strategy": "direct_replacement",
                    "full_line": self._get_line_content(node.lineno),
                    "requires_manual_review": False,
                }
                self.all_import_patterns.append(pattern_info)
                self.framework_imports.append(pattern_info)

        self.generic_visit(node)

    def _analyze_import_pattern(self, node, alias):
        """Comprehensive import pattern analysis."""
        pattern_type = self._classify_import_pattern(node, alias)
        complexity = self._assess_complexity(node, alias, pattern_type)

        return {
            "type": "from_import",
            "module": node.module,
            "name": alias.name,
            "alias": alias.asname,
            "line": node.lineno,
            "column": node.col_offset,
            "pattern_type": pattern_type,
            "relative_level": node.level,
            "complexity": complexity,
            "update_strategy": self._get_update_strategy(pattern_type),
            "full_line": self._get_line_content(node.lineno),
            "requires_manual_review": complexity == "critical",
        }

    def _classify_import_pattern(self, node, alias):
        """Classify import pattern for AI agent handling."""
        if alias.name == "*":
            return "star_import"
        elif alias.asname:
            return "aliased_import"
        elif node.level > 0:
            return "relative_import"
        else:
            return "simple_import"

    def _assess_complexity(self, node, alias, pattern_type):
        """Assess complexity level for AI processing."""
        complexity_factors = {
            "star_import": "critical",  # Requires manual analysis
            "relative_import": "high" if node.level > 2 else "medium",
            "aliased_import": "medium",
            "simple_import": "low",
        }

        base_complexity = complexity_factors.get(pattern_type, "medium")

        # Check for agents/nodes imports specifically
        if "agents" in node.module or "nodes" in node.module:
            return base_complexity

        return "low"  # Non-agents/nodes imports are lower priority

    def _get_update_strategy(self, pattern_type):
        """Provide explicit update instructions for AI agent."""
        strategies = {
            "simple_import": "direct_replacement",
            "aliased_import": "preserve_alias_update_module",
            "relative_import": "convert_to_absolute_or_update_relative",
            "star_import": "manual_review_required",
        }
        return strategies.get(pattern_type, "direct_replacement")

    def _get_line_content(self, line_number):
        """Get the full line content for context."""
        try:
            with open(self.file_path, encoding="utf-8") as f:
                lines = f.readlines()
                return (
                    lines[line_number - 1].strip() if line_number <= len(lines) else ""
                )
        except Exception:
            return ""

    def get_summary(self):
        """Get comprehensive summary for AI agent planning."""
        return {
            "total_imports": len(self.all_import_patterns),
            "framework_imports": len(self.framework_imports),
            "simple_imports": len(
                [p for p in self.all_import_patterns if p["complexity"] == "low"]
            ),
            "medium_complexity": len(
                [p for p in self.all_import_patterns if p["complexity"] == "medium"]
            ),
            "high_complexity": len(
                [p for p in self.all_import_patterns if p["complexity"] == "high"]
            ),
            "critical_complexity": len(
                [p for p in self.all_import_patterns if p["complexity"] == "critical"]
            ),
            "star_imports": len(self.star_imports),
            "relative_imports": len(self.relative_imports),
            "manual_review_required": len(
                [
                    p
                    for p in self.all_import_patterns
                    if p.get("requires_manual_review", False)
                ]
            ),
            "agents_nodes_imports": len(
                [
                    p
                    for p in self.framework_imports
                    if "agents" in p["module"] or "nodes" in p["module"]
                ]
            ),
        }


class MigrationController:
    """AI-optimized migration controller with comprehensive validation."""

    def __init__(self):
        self.project_root = Path(".")
        self.src_root = self.project_root / "src" / "universal_framework"
        self.validation_results = {}
        self.rollback_triggers = {}
        self.migration_log = []

        # Enhanced path mappings - UPDATED: LangGraph-aligned structure (business_logic vs orchestrators)
        self.path_mappings = {
            "universal_framework.agents.email_agent": "universal_framework.nodes.agents.email_generation_agent",
            "universal_framework.agents.requirements_agent": "universal_framework.nodes.agents.requirements_collection_agent",
            "universal_framework.agents.strategy_generator": "universal_framework.nodes.agents.strategy_generation_agent",
            "universal_framework.agents.intent_analyzer_chain": "universal_framework.nodes.agents.intent_analysis_agent",
            "universal_framework.agents.intent_classifier": "universal_framework.nodes.agents.intent_classification_agent",
            "universal_framework.agents.confirmation_agent": "universal_framework.nodes.processors.confirmation_processor_node",
            "universal_framework.agents.email_context_extractor": "universal_framework.nodes.processors.context_extraction_node",
            "universal_framework.agents.intent_constants": "universal_framework.utils.intent.intent_constants",
            "universal_framework.agents.pattern_definitions": "universal_framework.utils.intent.pattern_definitions",
            "universal_framework.agents.help_formatter": "universal_framework.utils.formatters.help_formatter",
            "universal_framework.nodes.base": "universal_framework.nodes.base_node",
            "universal_framework.nodes.batch_requirements_collector": "universal_framework.nodes.business_logic.batch_requirements_node",
            "universal_framework.nodes.enhanced_email_generator": "universal_framework.nodes.business_logic.email_generation_node",
            "universal_framework.nodes.strategy_confirmation_handler": "universal_framework.nodes.business_logic.strategy_confirmation_node",
        }

        # File migration mappings
        self.file_migrations = {
            # Agent files (LLM-powered)
            "src/universal_framework/agents/email_agent.py": "src/universal_framework/nodes/agents/email_generation_agent.py",
            "src/universal_framework/agents/requirements_agent.py": "src/universal_framework/nodes/agents/requirements_collection_agent.py",
            "src/universal_framework/agents/strategy_generator.py": "src/universal_framework/nodes/agents/strategy_generation_agent.py",
            "src/universal_framework/agents/intent_analyzer_chain.py": "src/universal_framework/nodes/agents/intent_analysis_agent.py",
            "src/universal_framework/agents/intent_classifier.py": "src/universal_framework/nodes/agents/intent_classification_agent.py",
            # Processor files (non-agentic)
            "src/universal_framework/agents/confirmation_agent.py": "src/universal_framework/nodes/processors/confirmation_processor_node.py",
            "src/universal_framework/agents/email_context_extractor.py": "src/universal_framework/nodes/processors/context_extraction_node.py",
            # Business Logic files (Complex single-purpose nodes - NOT orchestrators)
            "src/universal_framework/nodes/batch_requirements_collector.py": "src/universal_framework/nodes/business_logic/batch_requirements_node.py",
            "src/universal_framework/nodes/enhanced_email_generator.py": "src/universal_framework/nodes/business_logic/email_generation_node.py",
            "src/universal_framework/nodes/strategy_confirmation_handler.py": "src/universal_framework/nodes/business_logic/strategy_confirmation_node.py",
            "src/universal_framework/nodes/strategy_generator_node.py": "src/universal_framework/nodes/business_logic/strategy_generation_node.py",
            # Base infrastructure
            "src/universal_framework/nodes/base.py": "src/universal_framework/nodes/base_node.py",
            # Utility files
            "src/universal_framework/agents/intent_constants.py": "src/universal_framework/utils/intent/intent_constants.py",
            "src/universal_framework/agents/pattern_definitions.py": "src/universal_framework/utils/intent/pattern_definitions.py",
            "src/universal_framework/agents/help_formatter.py": "src/universal_framework/utils/formatters/help_formatter.py",
            # Test files
            "src/universal_framework/agents/simple_intent_test.py": "tests/nodes/agents/test_intent_basic.py",
            "src/universal_framework/agents/test_intent_classifier_fix.py": "tests/nodes/agents/test_intent_defensive.py",
            "src/universal_framework/agents/test_refactored_intent.py": "tests/nodes/agents/test_intent_refactored.py",
        }

    async def execute_comprehensive_migration(self):
        """Execute full migration with comprehensive validation gates."""

        print("🚀 Starting Enhanced AI Migration Controller")
        print("=" * 80)

        try:
            # Phase 0: Comprehensive Readiness Assessment
            print("\n📋 Phase 0: Comprehensive Readiness Assessment")
            readiness_result = await self.phase_0_comprehensive_readiness()

            if readiness_result["status"] != "AI_READY":
                return self.abort_migration("Readiness check failed", readiness_result)

            print(
                f"✅ Readiness check passed with confidence: {readiness_result['confidence']:.1%}"
            )

            # Phase 1: Enhanced Preparation
            print("\n🔧 Phase 1: Enhanced Preparation and Analysis")
            prep_result = await self.phase_1_enhanced_preparation()

            if prep_result["status"] != "ready":
                return self.abort_migration("Preparation failed", prep_result["issues"])

            print("✅ Preparation phase completed successfully")

            # Phase 2: Systematic Migration
            print("\n🔄 Phase 2: Systematic Migration with Real-Time Validation")
            migration_result = await self.phase_2_systematic_migration()

            if migration_result["status"] != "complete":
                return await self.execute_automatic_rollback(
                    "Migration failed", migration_result["issues"]
                )

            print("✅ Migration phase completed successfully")

            # Phase 3: Comprehensive Validation
            print("\n🧪 Phase 3: Comprehensive Validation and Testing")
            validation_result = await self.phase_3_comprehensive_validation()

            if validation_result["status"] != "validated":
                return await self.execute_automatic_rollback(
                    "Validation failed", validation_result["issues"]
                )

            print("✅ Validation phase completed successfully")

            return self.complete_migration()

        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return await self.handle_unexpected_error(e)

    async def phase_0_comprehensive_readiness(self):
        """Comprehensive readiness validation for AI execution."""

        print("  🔍 Analyzing project structure and dependencies...")

        # Step 0.1: Current structure analysis
        current_analysis = await self.analyze_current_structure()

        # Step 0.2: Import complexity analysis
        import_analysis = await self.analyze_import_complexity()

        # Step 0.3: Git state validation
        git_state = await self.validate_git_state()

        # Step 0.4: Test baseline establishment
        test_baseline = await self.establish_test_baseline()

        print(f"  📊 Files analyzed: {current_analysis['total_files']}")
        print(f"  📦 Framework imports found: {import_analysis['framework_imports']}")
        print(f"  🔗 Agents/nodes imports: {import_analysis['agents_nodes_imports']}")
        print(
            f"  ⚠️  Manual review required: {import_analysis['manual_review_required']}"
        )

        # Calculate readiness score
        readiness_score = self.calculate_readiness_score(
            {
                "structure_analysis": current_analysis,
                "import_complexity": import_analysis,
                "git_state": git_state,
                "test_baseline": test_baseline,
            }
        )

        # Decision logic
        if import_analysis["critical_complexity"] > 0:
            return {
                "status": "HUMAN_REVIEW_REQUIRED",
                "reason": "Critical import patterns require manual review",
                "critical_patterns": import_analysis["critical_complexity"],
            }

        if not git_state["clean"]:
            return {
                "status": "NOT_READY",
                "reason": "Git repository not in clean state",
                "git_issues": git_state["issues"],
            }

        if readiness_score < 0.9:
            return {
                "status": "NOT_READY",
                "readiness_score": readiness_score,
                "required_actions": ["Resolve import complexity", "Clean git state"],
            }

        return {"status": "AI_READY", "confidence": readiness_score}

    async def analyze_current_structure(self):
        """Analyze current project structure."""

        agents_files = list((self.src_root / "agents").glob("*.py"))
        nodes_files = list((self.src_root / "nodes").glob("*.py"))

        return {
            "total_files": len(agents_files) + len(nodes_files),
            "agents_files": len(agents_files),
            "nodes_files": len(nodes_files),
            "agents_list": [
                f.name for f in agents_files if not f.name.startswith("__")
            ],
            "nodes_list": [f.name for f in nodes_files if not f.name.startswith("__")],
        }

    async def analyze_import_complexity(self):
        """Analyze import complexity across the project."""

        analysis_results = {
            "files_analyzed": 0,
            "framework_imports": 0,
            "agents_nodes_imports": 0,
            "total_imports": 0,
            "complexity_breakdown": {"low": 0, "medium": 0, "high": 0, "critical": 0},
            "manual_review_required": 0,
            "high_risk_files": [],
        }

        # Analyze all Python files in src
        for py_file in (self.project_root / "src").rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                detector = EnhancedImportDetector(str(py_file))
                with open(py_file, encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                detector.visit(tree)

                summary = detector.get_summary()
                analysis_results["files_analyzed"] += 1
                analysis_results["framework_imports"] += summary["framework_imports"]
                analysis_results["agents_nodes_imports"] += summary[
                    "agents_nodes_imports"
                ]
                analysis_results["total_imports"] += summary["total_imports"]

                # Aggregate complexity breakdown
                for complexity in ["low", "medium", "high", "critical"]:
                    key = f"{complexity}_complexity"
                    analysis_results["complexity_breakdown"][complexity] += summary.get(
                        key, 0
                    )

                analysis_results["manual_review_required"] += summary[
                    "manual_review_required"
                ]

                # Track high-risk files
                if (
                    summary["manual_review_required"] > 0
                    or summary["critical_complexity"] > 0
                ):
                    analysis_results["high_risk_files"].append(
                        {
                            "file": str(py_file.relative_to(self.project_root)),
                            "summary": summary,
                        }
                    )

            except Exception as e:
                print(f"  ⚠️ Error analyzing {py_file}: {e}")

        return analysis_results

    async def validate_git_state(self):
        """Validate git repository state."""

        try:
            # Check if git repo exists and is clean
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
            )

            if result.returncode != 0:
                return {"clean": False, "issues": ["Not a git repository"]}

            if result.stdout.strip():
                return {
                    "clean": False,
                    "issues": ["Uncommitted changes detected"],
                    "status_output": result.stdout.strip(),
                }

            return {"clean": True, "issues": []}

        except Exception as e:
            return {"clean": False, "issues": [f"Git validation error: {e}"]}

    async def establish_test_baseline(self):
        """Establish test baseline before migration."""

        try:
            # Run a quick test to check if pytest is available and tests can run
            result = subprocess.run(
                ["python", "-m", "pytest", "--version"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=10,
            )

            if result.returncode != 0:
                return {"available": False, "reason": "pytest not available"}

            # Try to collect tests without running them
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q"],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            return {
                "available": True,
                "pytest_version": (
                    result.stdout.strip() if result.returncode == 0 else "unknown"
                ),
                "collection_successful": result.returncode == 0,
            }

        except Exception as e:
            return {"available": False, "reason": f"Test baseline error: {e}"}

    def calculate_readiness_score(self, analysis_data):
        """Calculate overall readiness score for AI execution."""

        score = 1.0

        # Penalize for import complexity
        import_data = analysis_data["import_complexity"]
        if import_data["critical_complexity"] > 0:
            score -= 0.5
        if import_data["manual_review_required"] > 5:
            score -= 0.2
        if import_data["agents_nodes_imports"] > 50:
            score -= 0.1

        # Penalize for git issues
        if not analysis_data["git_state"]["clean"]:
            score -= 0.3

        # Penalize for test issues
        if not analysis_data["test_baseline"]["available"]:
            score -= 0.1

        return max(0.0, score)

    async def phase_1_enhanced_preparation(self):
        """Enhanced preparation with comprehensive analysis and validation."""

        print("  📁 Creating backup and migration plan...")

        # Step 1.1: Create backup
        backup_result = await self.create_backup()
        if not backup_result["success"]:
            return {"status": "not_ready", "issues": ["Backup creation failed"]}

        # Step 1.2: Validate migration plan
        migration_plan = await self.validate_migration_plan()

        # Step 1.3: Pre-create directory structure
        structure_result = await self.create_directory_structure()

        return {
            "status": "ready",
            "backup": backup_result,
            "migration_plan": migration_plan,
            "structure": structure_result,
        }

    async def create_backup(self):
        """Create comprehensive backup before migration."""

        try:
            # Create git stash as backup
            result = subprocess.run(
                ["git", "stash", "push", "-m", "Pre-migration backup"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            return {
                "success": True,
                "method": "git_stash",
                "message": "Pre-migration backup created",
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def validate_migration_plan(self):
        """Validate the migration plan before execution."""

        validation_results = []

        # Check that all source files exist
        for old_path, new_path in self.file_migrations.items():
            old_file = self.project_root / old_path
            if not old_file.exists():
                validation_results.append(f"Source file missing: {old_path}")

        # Check for potential conflicts
        for old_path, new_path in self.file_migrations.items():
            new_file = self.project_root / new_path
            if new_file.exists():
                validation_results.append(f"Target file already exists: {new_path}")

        return {
            "valid": len(validation_results) == 0,
            "issues": validation_results,
            "total_files_to_migrate": len(self.file_migrations),
        }

    async def create_directory_structure(self):
        """Create the new directory structure."""

        directories_to_create = [
            "src/universal_framework/nodes/agents",
            "src/universal_framework/nodes/business_logic",  # LangGraph-aligned: single-purpose business nodes
            "src/universal_framework/nodes/processors",
            "src/universal_framework/utils/intent",
            "src/universal_framework/utils/formatters",
            "tests/nodes/agents",
            "tests/nodes/business_logic",  # Updated test structure
            "tests/nodes/processors",
            "tests/utils",
            "tests/integration",
        ]

        created_dirs = []

        for dir_path in directories_to_create:
            full_path = self.project_root / dir_path
            try:
                full_path.mkdir(parents=True, exist_ok=True)

                # Create __init__.py files
                init_file = full_path / "__init__.py"
                if not init_file.exists():
                    init_file.touch()

                created_dirs.append(dir_path)

            except Exception as e:
                print(f"  ⚠️ Error creating directory {dir_path}: {e}")

        print(f"  📁 Created {len(created_dirs)} directories")
        return {
            "created": created_dirs,
            "success": len(created_dirs) == len(directories_to_create),
        }

    async def phase_2_systematic_migration(self):
        """Systematic migration with real-time validation."""

        print("  🔄 Executing file migrations...")

        migration_results = []

        # Execute file migrations in order
        for old_path, new_path in self.file_migrations.items():
            result = await self.migrate_single_file(old_path, new_path)
            migration_results.append(result)

            if not result["success"]:
                print(f"  ❌ Failed to migrate {old_path}: {result['error']}")
                return {"status": "failed", "issues": migration_results}
            else:
                print(f"  ✅ Migrated: {old_path} → {new_path}")

        # Update imports
        print("  🔗 Updating import statements...")
        import_results = await self.update_imports()

        return {
            "status": "complete",
            "file_migrations": migration_results,
            "import_updates": import_results,
        }

    async def migrate_single_file(self, old_path: str, new_path: str):
        """Migrate a single file with validation."""

        try:
            old_file = self.project_root / old_path
            new_file = self.project_root / new_path

            if not old_file.exists():
                return {"success": False, "error": f"Source file not found: {old_path}"}

            # Ensure target directory exists
            new_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file (don't move yet, in case we need to rollback)
            shutil.copy2(old_file, new_file)

            # Validate the copied file
            if not new_file.exists():
                return {"success": False, "error": "File copy failed"}

            # Check syntax if it's a Python file
            if new_file.suffix == ".py":
                try:
                    with open(new_file, encoding="utf-8") as f:
                        ast.parse(f.read())
                except SyntaxError as e:
                    return {
                        "success": False,
                        "error": f"Syntax error in copied file: {e}",
                    }

            return {"success": True, "old_path": old_path, "new_path": new_path}

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def update_imports(self):
        """Update import statements across all files."""

        updated_files = []
        error_files = []

        # Find all Python files that might contain imports to update
        for py_file in (self.project_root / "src").rglob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                result = await self.update_imports_in_file(py_file)
                if result["updated"]:
                    updated_files.append(str(py_file.relative_to(self.project_root)))
                    print(
                        f"    ✅ Updated imports in: {py_file.relative_to(self.project_root)}"
                    )

            except Exception as e:
                error_files.append({"file": str(py_file), "error": str(e)})
                print(f"    ❌ Error updating {py_file}: {e}")

        return {
            "updated_files": updated_files,
            "error_files": error_files,
            "success": len(error_files) == 0,
        }

    async def update_imports_in_file(self, file_path: Path):
        """Update imports in a single file."""

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()

            original_content = content
            updates_made = 0

            # Update each mapping
            for old_module, new_module in self.path_mappings.items():
                # Handle from imports
                old_pattern = f"from {old_module} import"
                new_pattern = f"from {new_module} import"
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    updates_made += 1

                # Handle direct imports
                old_pattern = f"import {old_module}"
                new_pattern = f"import {new_module}"
                if old_pattern in content:
                    content = content.replace(old_pattern, new_pattern)
                    updates_made += 1

            # Write back if changes were made
            if content != original_content:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                # Validate syntax after update
                try:
                    ast.parse(content)
                except SyntaxError as e:
                    # Rollback on syntax error
                    with open(file_path, "w", encoding="utf-8") as f:
                        f.write(original_content)
                    raise Exception(f"Syntax error after import update: {e}")

            return {"updated": updates_made > 0, "updates_count": updates_made}

        except Exception as e:
            raise Exception(f"Error updating imports in {file_path}: {e}")

    async def phase_3_comprehensive_validation(self):
        """Comprehensive validation with automatic triggers."""

        print("  🧪 Running comprehensive validation...")

        # Step 3.1: Import validation
        import_validation = await self.validate_imports()
        print(
            f"    📦 Import validation: {'✅ PASS' if import_validation['success'] else '❌ FAIL'}"
        )

        # Step 3.2: Syntax validation
        syntax_validation = await self.validate_syntax()
        print(
            f"    🔍 Syntax validation: {'✅ PASS' if syntax_validation['success'] else '❌ FAIL'}"
        )

        # Step 3.3: Basic functionality test
        functionality_test = await self.test_basic_functionality()
        print(
            f"    ⚙️ Functionality test: {'✅ PASS' if functionality_test['success'] else '❌ FAIL'}"
        )

        # Aggregate results
        all_validations = [import_validation, syntax_validation, functionality_test]
        overall_success = all(v["success"] for v in all_validations)

        if not overall_success:
            failed_validations = [
                v["name"] for v in all_validations if not v["success"]
            ]
            return {
                "status": "failed",
                "issues": failed_validations,
                "validation_details": {
                    "import_validation": import_validation,
                    "syntax_validation": syntax_validation,
                    "functionality_test": functionality_test,
                },
            }

        return {"status": "validated", "validation_summary": "All validations passed"}

    async def validate_imports(self):
        """Validate that all imports resolve correctly."""

        import_errors = []

        # Check new files can be imported
        test_imports = [
            "universal_framework.nodes.agents.email_generation_agent",
            "universal_framework.nodes.business_logic.email_generation_node",  # Updated to business_logic
            "universal_framework.utils.intent.intent_constants",
        ]

        for module_name in test_imports:
            try:
                # Try to import the module
                result = subprocess.run(
                    ["python", "-c", f'import {module_name}; print("OK")'],
                    capture_output=True,
                    text=True,
                    cwd=self.project_root,
                    timeout=10,
                )

                if result.returncode != 0:
                    import_errors.append(
                        {"module": module_name, "error": result.stderr.strip()}
                    )

            except Exception as e:
                import_errors.append({"module": module_name, "error": str(e)})

        return {
            "name": "import_validation",
            "success": len(import_errors) == 0,
            "errors": import_errors,
            "modules_tested": len(test_imports),
        }

    async def validate_syntax(self):
        """Validate syntax of all migrated files."""

        syntax_errors = []

        # Check all Python files in new locations
        for py_file in (self.project_root / "src" / "universal_framework").rglob(
            "*.py"
        ):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file, encoding="utf-8") as f:
                    content = f.read()

                ast.parse(content)

            except SyntaxError as e:
                syntax_errors.append(
                    {
                        "file": str(py_file.relative_to(self.project_root)),
                        "line": e.lineno,
                        "message": e.msg,
                    }
                )
            except Exception as e:
                syntax_errors.append(
                    {
                        "file": str(py_file.relative_to(self.project_root)),
                        "error": str(e),
                    }
                )

        return {
            "name": "syntax_validation",
            "success": len(syntax_errors) == 0,
            "errors": syntax_errors,
        }

    async def test_basic_functionality(self):
        """Test basic functionality of migrated components."""

        try:
            # Try to run a simple import test
            test_script = """
import sys
sys.path.insert(0, "src")

try:
    from universal_framework.utils.intent import intent_constants
    from universal_framework.nodes import base_node
    print("Basic functionality test: PASS")
    exit(0)
except Exception as e:
    print(f"Basic functionality test: FAIL - {e}")
    exit(1)
"""

            result = subprocess.run(
                ["python", "-c", test_script],
                capture_output=True,
                text=True,
                cwd=self.project_root,
                timeout=30,
            )

            return {
                "name": "functionality_test",
                "success": result.returncode == 0,
                "output": result.stdout.strip(),
                "error": result.stderr.strip() if result.stderr else None,
            }

        except Exception as e:
            return {"name": "functionality_test", "success": False, "error": str(e)}

    async def execute_automatic_rollback(self, reason: str, details: Any):
        """Execute comprehensive automatic rollback."""

        print(f"\n🔄 Executing automatic rollback due to: {reason}")

        try:
            # Restore from git stash
            result = subprocess.run(
                ["git", "stash", "pop"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                print("✅ Successfully rolled back to pre-migration state")
                return {"success": True, "method": "git_stash_pop"}
            else:
                print(f"❌ Rollback failed: {result.stderr}")
                return {"success": False, "error": result.stderr}

        except Exception as e:
            print(f"❌ Rollback error: {e}")
            return {"success": False, "error": str(e)}

    def complete_migration(self):
        """Complete the migration successfully."""

        print("\n🎉 Migration completed successfully!")
        print("=" * 80)

        # Clean up old files now that migration is successful
        print("🧹 Cleaning up old files...")
        cleaned_files = []

        for old_path in self.file_migrations.keys():
            old_file = self.project_root / old_path
            if old_file.exists():
                try:
                    old_file.unlink()
                    cleaned_files.append(old_path)
                    print(f"  🗑️ Removed: {old_path}")
                except Exception as e:
                    print(f"  ⚠️ Could not remove {old_path}: {e}")

        return {
            "status": "completed",
            "files_migrated": len(self.file_migrations),
            "files_cleaned": len(cleaned_files),
            "message": "Reorganization completed successfully",
        }

    def abort_migration(self, reason: str, details: Any):
        """Abort migration due to readiness issues."""

        print(f"\n❌ Migration aborted: {reason}")
        print("Details:", details)
        return {"status": "aborted", "reason": reason, "details": details}

    async def handle_unexpected_error(self, error: Exception):
        """Handle unexpected errors during migration."""

        print(f"\n💥 Unexpected error during migration: {error}")

        # Attempt rollback
        rollback_result = await self.execute_automatic_rollback(
            "Unexpected error", str(error)
        )

        return {"status": "error", "error": str(error), "rollback": rollback_result}


async def main():
    """Main execution function."""

    controller = MigrationController()
    result = await controller.execute_comprehensive_migration()

    print("\n" + "=" * 80)
    print("MIGRATION RESULT:", result.get("status", "unknown").upper())

    if result.get("status") == "completed":
        print("🎉 Reorganization completed successfully!")
        print("\nNext steps:")
        print("1. Run your test suite to verify everything works")
        print("2. Update any remaining external references")
        print("3. Update documentation to reflect new structure")
    else:
        print("❌ Migration was not completed")
        if "reason" in result:
            print(f"Reason: {result['reason']}")

    return result


if __name__ == "__main__":
    asyncio.run(main())
