# Legacy Intent Classifier Cleanup Plan

## Overview

This document outlines the systematic cleanup of legacy intent classification code after successful integration of the new conversation-aware LangGraph workflow routing system. The cleanup removes duplicated, outdated, and conflicting code patterns while preserving essential functionality.

## Legacy Code Analysis

### 🚨 Critical Legacy Files Identified

#### 1. **Primary Legacy File (HIGH PRIORITY)**
- **File**: `src/universal_framework/utils/intent_classifier.py`
- **Status**: LEGACY - Contains duplicate IntentClassifier implementation
- **Issues**:
  - Duplicates functionality now in `src/universal_framework/agents/intent_classifier.py`
  - Uses outdated pattern-only classification (no LLM support)
  - Missing conversation-aware capabilities
  - Conflicts with new LangGraph integration
  - Uses deprecated imports and patterns

#### 2. **Test Files with Legacy References (MEDIUM PRIORITY)**
- **Files**:
  - `.temp/temp_test_openai_fix.py`
  - `.temp/temp_quick_fix_test.py` 
  - `src/universal_framework/agents/test_refactored_intent.py`
  - `src/universal_framework/agents/test_intent_classifier_fix.py`
- **Issues**:
  - Reference outdated intent classifier implementations
  - Some contain hardcoded test logic that conflicts with actual implementation
  - Mix of legacy and new patterns in same files
  - Temporary test files left in wrong locations

#### 3. **Documentation with Outdated Patterns (LOW PRIORITY)**
- **Files**:
  - Various blueprint files referencing old patterns
  - Configuration examples using deprecated methods
- **Issues**:
  - Documentation shows legacy usage patterns
  - May confuse developers about correct implementation approach

### 🏗️ Current Architecture State

#### New LangGraph-Integrated System (KEEP)
- **Primary File**: `src/universal_framework/agents/intent_classifier.py`
- **Features**:
  - ✅ Conversation-aware classification with `AsyncConversationAwareIntentClassifier`
  - ✅ Multi-tier classification (conversation → LLM → patterns)
  - ✅ LangGraph workflow integration
  - ✅ Modern Python 3.11+ features (match/case, union types)
  - ✅ Defensive programming for state access
  - ✅ Enterprise logging and tracing
  - ✅ Async-first architecture

#### Supporting Infrastructure (KEEP)
- **Files**:
  - `src/universal_framework/agents/intent_analyzer_chain.py` - SalesGPT-based conversation-aware classifier
  - `src/universal_framework/workflow/intent_classification_nodes.py` - LangGraph node integration
  - `src/universal_framework/agents/intent_constants.py` - Shared constants
  - `src/universal_framework/agents/pattern_definitions.py` - Pattern management
  - `src/universal_framework/agents/email_context_extractor.py` - Context extraction
  - `src/universal_framework/agents/help_formatter.py` - Response formatting

## Cleanup Implementation Plan

### Phase 1: Remove Primary Legacy File ⚠️ BREAKING CHANGE

#### Step 1.1: Analyze Dependencies
```bash
# Search for imports of legacy file
grep -r "from universal_framework.utils.intent_classifier" src/
grep -r "import universal_framework.utils.intent_classifier" src/
```

#### Step 1.2: Update Import References
- **Target Files to Update**:
  - Any files importing from `utils.intent_classifier`
  - Update to import from `agents.intent_classifier`

#### Step 1.3: Remove Legacy File
```bash
# After confirming no critical dependencies
rm src/universal_framework/utils/intent_classifier.py
```

### Phase 2: Clean Up Temporary Test Files

#### Step 2.1: Remove Temporary Files
```bash
rm .temp/temp_test_openai_fix.py
rm .temp/temp_quick_fix_test.py
```

#### Step 2.2: Consolidate Test Logic
- **Target Files**:
  - `src/universal_framework/agents/test_refactored_intent.py`
  - `src/universal_framework/agents/test_intent_classifier_fix.py`
- **Actions**:
  - Extract useful test cases into proper test files in `tests/agents/`
  - Remove redundant standalone test files
  - Update to use new intent classifier implementation

### Phase 3: Update Documentation

#### Step 3.1: Update Code Examples
- **Target Files**:
  - `docs/planning/conversation_aware_intent_classification_blueprint.md`
  - Configuration files with old patterns
- **Actions**:
  - Update examples to use new conversation-aware classifier
  - Remove references to legacy pattern-only classification
  - Update import statements in documentation

#### Step 3.2: Archive Legacy Documentation
- **Actions**:
  - Move outdated implementation details to `docs/archive/`
  - Update current documentation to reflect new architecture

### Phase 4: Validation and Testing

#### Step 4.1: Regression Testing
```bash
# Run existing tests to ensure no breaking changes
pytest tests/agents/test_conversation_aware_intent_classifier.py -v
pytest tests/agents/ -k "intent" -v
```

#### Step 4.2: Integration Testing
```bash
# Test LangGraph workflow integration
python -m pytest tests/workflow/ -k "intent" -v
```

#### Step 4.3: API Endpoint Testing
```bash
# Test API endpoints still work with new classifier
python -m pytest tests/api/ -k "workflow" -v
```

## Risk Assessment

### 🔴 High Risk Areas

#### Import Dependencies
- **Risk**: Other modules importing from legacy `utils.intent_classifier`
- **Mitigation**: Thorough dependency analysis before removal
- **Fallback**: Create import alias in `utils/__init__.py` if needed

#### Test Coverage Gaps
- **Risk**: Removing test files may reduce coverage
- **Mitigation**: Extract useful test cases before deletion
- **Validation**: Run coverage reports before/after cleanup

### 🟡 Medium Risk Areas

#### Backward Compatibility
- **Risk**: External code expecting old API interface
- **Mitigation**: Maintain public API compatibility in new implementation
- **Timeline**: Plan deprecation warnings before removal

#### Configuration Dependencies
- **Risk**: Config files or environment setup expecting old paths
- **Mitigation**: Update all configuration references
- **Testing**: Full environment validation after changes

### 🟢 Low Risk Areas

#### Documentation Updates
- **Impact**: Minimal operational risk
- **Timeline**: Can be done incrementally
- **Priority**: Update after code changes are stable

## Implementation Timeline

### Week 1: Analysis and Preparation
- [ ] Complete dependency analysis
- [ ] Identify all import references
- [ ] Extract valuable test cases from legacy files
- [ ] Create backup branch for rollback safety

### Week 2: Code Cleanup
- [ ] Remove primary legacy file (`utils/intent_classifier.py`)
- [ ] Update all import references
- [ ] Clean up temporary test files
- [ ] Consolidate test logic into proper test files

### Week 3: Documentation and Validation
- [ ] Update documentation with new patterns
- [ ] Run comprehensive regression testing
- [ ] Validate API endpoints and workflow integration
- [ ] Performance testing of new vs old implementation

### Week 4: Final Validation
- [ ] End-to-end testing in development environment
- [ ] Security review of changes
- [ ] Documentation review and approval
- [ ] Production deployment plan

## Success Criteria

### ✅ Technical Success Metrics
- [ ] All tests pass with new implementation
- [ ] No performance regression (< 5% latency increase acceptable)
- [ ] Zero breaking changes to public APIs
- [ ] All imports updated to new locations
- [ ] Documentation reflects current architecture

### ✅ Code Quality Metrics
- [ ] Reduced code duplication (target: < 5% overlap)
- [ ] Improved maintainability (single source of truth for intent classification)
- [ ] Modern Python patterns throughout (match/case, union types, async-first)
- [ ] Consistent error handling and logging patterns

### ✅ Architecture Compliance
- [ ] Full LangGraph integration
- [ ] Conversation-aware classification operational
- [ ] Defensive programming patterns implemented
- [ ] Enterprise logging and tracing functional

## Rollback Plan

### Emergency Rollback
1. **Git Reset**: `git reset --hard [backup-commit-hash]`
2. **Import Restoration**: Restore legacy `utils/intent_classifier.py`
3. **Configuration Rollback**: Revert any config changes
4. **Test Validation**: Run full test suite to confirm functionality

### Gradual Rollback (If Partial Issues)
1. **Feature Flag Disable**: Disable conversation-aware classification
2. **Fallback Routes**: Activate legacy classification as fallback
3. **Monitoring**: Increase logging to identify specific issues
4. **Selective Fixes**: Address individual components without full rollback

## Post-Cleanup Monitoring

### Performance Monitoring
- **Metrics**: Intent classification latency, accuracy, error rates
- **Duration**: 2 weeks post-deployment
- **Thresholds**: < 500ms P95 latency, > 95% success rate

### Error Monitoring
- **Focus Areas**: Import errors, classification failures, API response times
- **Alerting**: Immediate notification for classification error rate > 1%
- **Logging**: Enhanced logging for first 48 hours post-deployment

## Conclusion

This cleanup plan systematically removes legacy intent classification code while preserving all functional capabilities in the new conversation-aware, LangGraph-integrated system. The phased approach minimizes risk while ensuring complete migration to modern patterns.

**Key Benefits Post-Cleanup**:
- Single source of truth for intent classification
- Modern conversation-aware capabilities
- Full LangGraph workflow integration
- Reduced maintenance overhead
- Improved performance and accuracy
- Consistent enterprise patterns throughout

**Next Steps**: Begin Phase 1 dependency analysis and create backup branch for safe implementation.
