# Story Definition of Done (DoD)

## Description
Developer self-validation checklist to ensure a user story meets all acceptance criteria and quality standards before marking it as complete. This checklist should be executed by the developer agent after implementing a story.

## Checklist Items

### Requirements & Acceptance Criteria
<!-- LLM: Verify that all acceptance criteria listed in the story are fully implemented and working as expected -->
- [ ] All acceptance criteria from the story are implemented
<!-- LLM: Check if the implementation matches the business requirements and user needs described -->
- [ ] Implementation matches business requirements
<!-- LLM: Verify edge cases and error scenarios are handled appropriately -->
- [ ] Edge cases and error scenarios are handled
<!-- LLM: Confirm that the user experience flows smoothly without issues -->
- [ ] User experience is smooth and intuitive

### Code Quality
<!-- LLM: Check if the code follows established coding standards and conventions -->
- [ ] Code follows project coding standards
<!-- LLM: Verify that the code is clean, readable, and well-organized -->
- [ ] Code is clean and readable
<!-- LLM: Check for proper error handling and logging throughout the implementation -->
- [ ] Proper error handling is implemented
<!-- LLM: Verify that no debugging code, console.logs, or temporary code remains -->
- [ ] No debugging code or TODOs remain
<!-- LLM: Check if the implementation follows SOLID principles and design patterns where appropriate -->
- [ ] SOLID principles are followed where applicable

### Testing
<!-- LLM: Verify that unit tests exist and cover the main functionality -->
- [ ] Unit tests are written and passing
<!-- LLM: Check if integration tests are implemented for API endpoints or service interactions -->
- [ ] Integration tests are implemented where needed
<!-- LLM: Verify that the test coverage meets project standards (usually >80%) -->
- [ ] Test coverage meets project standards
<!-- LLM: Confirm that all existing tests still pass after the changes -->
- [ ] All existing tests pass (no regressions)
<!-- LLM: Check if edge cases and error conditions are covered by tests -->
- [ ] Edge cases are covered by tests

### Documentation
<!-- LLM: Verify that code comments exist for complex logic and algorithms -->
- [ ] Code is properly commented
<!-- LLM: Check if API documentation is updated with new endpoints or changes -->
- [ ] API documentation is updated
<!-- LLM: Verify that README or user documentation reflects any user-facing changes -->
- [ ] User documentation is updated if needed
<!-- LLM: Check if technical documentation explains architectural decisions or complex implementations -->
- [ ] Technical documentation is complete
<!-- LLM: Verify that any configuration changes are documented -->
- [ ] Configuration changes are documented

### Security & Performance
<!-- LLM: Check for common security vulnerabilities (SQL injection, XSS, etc.) -->
- [ ] Security best practices are followed
<!-- LLM: Verify that sensitive data is properly protected and not logged -->
- [ ] No sensitive data is exposed or logged
<!-- LLM: Check if authentication and authorization are properly implemented -->
- [ ] Authentication/authorization is properly implemented
<!-- LLM: Verify that the implementation performs efficiently without obvious bottlenecks -->
- [ ] Performance is acceptable (no obvious bottlenecks)
<!-- LLM: Check if database queries are optimized and indexed properly -->
- [ ] Database queries are optimized

### Version Control
<!-- LLM: Verify that commits have clear, descriptive messages -->
- [ ] Commits have clear, descriptive messages
<!-- LLM: Check if the branch follows naming conventions -->
- [ ] Branch follows naming conventions
<!-- LLM: Verify that there are no merge conflicts with the target branch -->
- [ ] No merge conflicts with target branch
<!-- LLM: Check if the PR/MR description clearly explains the changes -->
- [ ] Pull request description is complete

### Deployment & Operations
<!-- LLM: Verify that any required database migrations are included -->
- [ ] Database migrations are included if needed
<!-- LLM: Check if environment variables and configuration are properly set -->
- [ ] Environment variables are configured
<!-- LLM: Verify that deployment scripts or CI/CD pipelines are updated -->
- [ ] Deployment process is updated if needed
<!-- LLM: Check if monitoring and logging are properly configured -->
- [ ] Monitoring and logging are in place
<!-- LLM: Verify that rollback procedures are documented if needed -->
- [ ] Rollback plan exists for risky changes

## Quality Gate Criteria

- **PASS**: All required items are checked (>95% completion)
- **CONCERNS**: Most items checked but some minor issues (80-95% completion)
- **FAIL**: Significant items unchecked (<80% completion)
- **WAIVED**: Special circumstances with documented justification

## Notes

This checklist should be executed by the developer agent after completing story implementation and before marking the story as done. Any unchecked items should have clear justification for why they are not applicable or not done.