# Architecture Review Checklist

## Description
Technical architecture validation checklist to ensure system design meets quality attributes, follows best practices, and aligns with organizational standards. This checklist should be executed by the architect agent when reviewing architecture documents or implementation.

## Checklist Items

### System Design & Structure
<!-- LLM: Verify that the architecture follows established patterns (microservices, monolithic, serverless, etc.) -->
- [ ] Architecture follows appropriate design patterns
<!-- LLM: Check if components have clear boundaries and responsibilities -->
- [ ] Components have clear separation of concerns
<!-- LLM: Verify that dependencies between components are well-defined and documented -->
- [ ] Dependencies are clearly defined and minimized
<!-- LLM: Check if the architecture supports the expected scale and growth -->
- [ ] System is designed for expected scale
<!-- LLM: Verify that there are no circular dependencies or architectural anti-patterns -->
- [ ] No circular dependencies or anti-patterns present

### Quality Attributes
<!-- LLM: Verify that performance requirements are addressed in the design -->
- [ ] Performance requirements are addressed
<!-- LLM: Check if scalability concerns are properly handled (horizontal/vertical scaling) -->
- [ ] Scalability strategy is defined and appropriate
<!-- LLM: Verify that reliability and fault tolerance mechanisms are in place -->
- [ ] Reliability and fault tolerance are built-in
<!-- LLM: Check if security is considered at the architecture level -->
- [ ] Security is addressed at architecture level
<!-- LLM: Verify that the system is maintainable and extensible -->
- [ ] Maintainability and extensibility are considered

### Technology Stack
<!-- LLM: Check if technology choices are justified and appropriate -->
- [ ] Technology choices are justified and documented
<!-- LLM: Verify that the team has expertise in chosen technologies -->
- [ ] Team has expertise in chosen technologies
<!-- LLM: Check if technologies are compatible and well-integrated -->
- [ ] Technologies are compatible with each other
<!-- LLM: Verify that licenses are appropriate for the use case -->
- [ ] License compliance is verified
<!-- LLM: Check if the technology stack is up-to-date and supported -->
- [ ] Technologies are current and actively maintained

### Data Architecture
<!-- LLM: Verify that data models are well-designed and normalized appropriately -->
- [ ] Data models are properly designed
<!-- LLM: Check if data flow between components is clear and efficient -->
- [ ] Data flow is documented and optimized
<!-- LLM: Verify that data consistency strategies are defined (eventual, strong, etc.) -->
- [ ] Data consistency strategy is appropriate
<!-- LLM: Check if backup and recovery procedures are defined -->
- [ ] Backup and recovery procedures are defined
<!-- LLM: Verify that data privacy and compliance requirements are met -->
- [ ] Data privacy and compliance are addressed

### Integration & APIs
<!-- LLM: Check if APIs follow consistent design principles (REST, GraphQL, etc.) -->
- [ ] APIs follow consistent design principles
<!-- LLM: Verify that API contracts are well-defined and versioned -->
- [ ] API contracts are clearly defined
<!-- LLM: Check if integration points are properly documented -->
- [ ] Integration points are documented
<!-- LLM: Verify that error handling and retry logic are defined -->
- [ ] Error handling strategies are defined
<!-- LLM: Check if rate limiting and throttling are considered -->
- [ ] Rate limiting and throttling are implemented

### Infrastructure & Deployment
<!-- LLM: Verify that infrastructure requirements are clearly defined -->
- [ ] Infrastructure requirements are documented
<!-- LLM: Check if deployment architecture supports CI/CD -->
- [ ] CI/CD pipeline is defined and appropriate
<!-- LLM: Verify that environments (dev, staging, prod) are properly separated -->
- [ ] Environment separation is maintained
<!-- LLM: Check if containerization/orchestration is used appropriately -->
- [ ] Container strategy is appropriate if used
<!-- LLM: Verify that infrastructure as code principles are followed -->
- [ ] Infrastructure as Code (IaC) is implemented

### Monitoring & Operations
<!-- LLM: Check if monitoring strategy covers all critical components -->
- [ ] Comprehensive monitoring strategy is defined
<!-- LLM: Verify that logging is structured and centralized -->
- [ ] Logging strategy is appropriate and centralized
<!-- LLM: Check if alerting thresholds and procedures are defined -->
- [ ] Alerting and incident response are defined
<!-- LLM: Verify that performance metrics and KPIs are identified -->
- [ ] Key performance indicators are identified
<!-- LLM: Check if operational runbooks exist for common scenarios -->
- [ ] Operational procedures are documented

### Security Architecture
<!-- LLM: Verify that authentication and authorization are properly designed -->
- [ ] Authentication/authorization design is robust
<!-- LLM: Check if data encryption is implemented (at rest and in transit) -->
- [ ] Data encryption is properly implemented
<!-- LLM: Verify that security boundaries and zones are defined -->
- [ ] Security boundaries are clearly defined
<!-- LLM: Check if threat modeling has been performed -->
- [ ] Threat modeling has been conducted
<!-- LLM: Verify that security testing strategy is defined -->
- [ ] Security testing approach is defined

### Documentation & Communication
<!-- LLM: Check if architecture diagrams are complete and up-to-date -->
- [ ] Architecture diagrams are comprehensive
<!-- LLM: Verify that architectural decisions are documented (ADRs) -->
- [ ] Architectural Decision Records (ADRs) exist
<!-- LLM: Check if component interfaces are well-documented -->
- [ ] Component interfaces are documented
<!-- LLM: Verify that deployment guides are complete -->
- [ ] Deployment documentation is complete
<!-- LLM: Check if architecture is understandable to all stakeholders -->
- [ ] Documentation is accessible to stakeholders

### Risk Management
<!-- LLM: Verify that technical risks are identified and mitigated -->
- [ ] Technical risks are identified and addressed
<!-- LLM: Check if single points of failure are eliminated -->
- [ ] Single points of failure are minimized
<!-- LLM: Verify that disaster recovery plan exists -->
- [ ] Disaster recovery plan is defined
<!-- LLM: Check if capacity planning has been performed -->
- [ ] Capacity planning is documented
<!-- LLM: Verify that technical debt is acknowledged and planned for -->
- [ ] Technical debt is tracked and managed

## Quality Gate Criteria

- **PASS**: Architecture meets all critical requirements (>90% completion)
- **CONCERNS**: Architecture is sound but has minor issues (75-90% completion)
- **FAIL**: Significant architectural issues need addressing (<75% completion)
- **WAIVED**: Special circumstances with executive approval

## Notes

This checklist should be executed during architecture reviews, before major implementations, and when evaluating system changes. The architect agent should provide detailed justifications for any unchecked items and recommendations for improvements.