# META SENTINEL — MASTER PROJECT BRIEF AND EXECUTION DIRECTIVE

(From Del, 2026-10-28. Posted to the crew bus room 1 by Pax at Del's order.)

## 1. PROJECT IDENTITY

Project name: Meta Sentinel

Competition: Meta Global AI Developer Hackathon 2026
Track: Indie — Push the Frontier
Deadline: November 4, 2026, at 9:00 PM Eastern Time

Current status: Greenfield project. Assume nothing has been implemented yet unless you verify it.

Available resources: Four AI coding agents, access to Meta's AI tooling where available, and the ability to develop and demonstrate a working prototype.

You are part of the engineering team responsible for turning Meta Sentinel into a functional, technically credible hackathon submission.

This is not an exercise in brainstorming, writing a product proposal, or generating an attractive mockup. We need working software that demonstrates a real capability, can be tested against actual scenarios, and can withstand scrutiny from technical judges.

You must prioritize execution, measurable performance, technical depth, and a reliable live demonstration.

## 2. THE CORE IDEA

Meta Sentinel is a prototype for real-time visual event detection using multimodal AI.

The long-term concept is to build specialized visual intelligence systems that help people identify potentially important events in environments where visual monitoring is useful.

Possible applications include:

* Public safety and incident awareness.
* Fire and smoke detection.
* Identification of unusual visual events that warrant human review.
* Situational awareness for emergency response.
* Other specialized visual monitoring applications.

However, we are NOT attempting to build an entire government operating system or a complete police or fire department platform before the deadline.

We are building one focused, demonstrable capability that could serve as the foundation for a larger system.

### Initial prototype

The first prototype should use a phone camera or webcam to capture a consenting participant performing staged actions.

The system analyzes the visual input and produces structured observations about what is happening.

For example, a participant might:

* Dance.
* Walk normally.
* Wave their arms.
* Simulate an argument.
* Perform a staged physical altercation.
* Raise their hands.
* Fall or deliberately sit down.
* Perform an ambiguous action that could be misinterpreted.

The system should attempt to distinguish observable actions and events, explain why it flagged an event, and communicate uncertainty.

The purpose is to test the model's actual visual reasoning capabilities, including its ability to recognize ambiguous situations and avoid false alarms.

Critical distinction: Detecting a fight-like movement is not the same as establishing that an assault or crime has occurred. The system must report observable evidence and uncertainty, not pretend to determine criminal intent.

## 3. THE RESEARCH QUESTION

The central question is:

Can we build a working system that converts visual input into useful, structured, evidence-supported event assessments, while measuring how often the system is correct and how often it makes mistakes?

We need to go beyond sending an image to a model and displaying whatever text it returns.

The system should demonstrate an actual pipeline:

1. Acquire visual input.
2. Process the input using an appropriate computer vision or multimodal model.
3. Identify observable actions or potential events.
4. Produce a structured event assessment.
5. Associate the assessment with relevant visual evidence and a timestamp.
6. Apply confidence and uncertainty handling.
7. Display the result in a usable interface.
8. Record the result for evaluation.
9. Compare predictions with known ground truth from staged test scenarios.
10. Report performance honestly.

We must establish whether this pipeline provides meaningful value beyond a generic vision-model chat interface.

If the implementation does not outperform a simpler baseline or demonstrate another measurable advantage, acknowledge that result and investigate the cause.

Do not manufacture results.

## 4. META AI TOOLING

The project should investigate and use the relevant Meta AI capabilities available to this hackathon.

Potential tools include:

### Muse Spark

* Investigate its actual supported multimodal input capabilities.
* Determine how it can interpret visual evidence, reason about events, and return structured assessments.
* Verify API availability, authentication, rate limits, supported input formats, and deployment constraints before committing to an implementation.
* Do not assume that a text-only endpoint can accept continuous video.

### SAM 3.1

* Investigate its supported visual segmentation and object identification capabilities.
* Determine whether it can help isolate relevant objects, people, or regions in the scene.
* Use it only where it provides a measurable technical benefit.

### Muse Image / Wonder

* Evaluate whether image generation or editing has a meaningful role in the prototype.
* Do not integrate image-generation tools merely to increase the number of Meta products listed in the submission.

The specific product names, availability, SDKs, and supported capabilities must be verified against current official documentation and the hackathon rules.

Do not invent APIs, endpoints, model capabilities, or access credentials.

### Integration principle

Each model must have a defined responsibility.

For example, a segmentation model might isolate a relevant region, while a reasoning model interprets selected visual evidence and generates an event assessment.

This is only a proposed architecture. Validate that it is technically feasible and improves the result before adopting it.

A smaller, functional system using two well-integrated capabilities is preferable to a larger system with several superficial integrations.

## 5. THE FOUR-AGENT ENGINEERING TEAM

We have four AI coding agents available.

Divide the work into parallel tasks with explicit ownership, shared interfaces, and independently verifiable deliverables.

Do not allow all four agents to independently design the same application.

### Agent 1 — Frontend and Camera Interface

Responsibilities:

* Build the primary user interface.
* Implement camera permission handling.
* Capture video from the user's device where supported.
* Provide start, stop, and reset controls.
* Display the current analysis state.
* Display detected events, timestamps, explanations, and uncertainty.
* Show an event history or timeline.
* Provide useful loading, error, and permission-denied states.
* Make the interface usable on a phone and desktop.

Requirements:

* Use real application state.
* Connect the interface to the actual analysis pipeline.
* Do not substitute hardcoded detection results for working functionality.
* Avoid unnecessary visual effects, decorative gradients, excessive rounded cards, and other styling that distracts from the demonstration.
* Keep the interface clear, restrained, and operational.

Deliverables:

* Working camera interface.
* Documented integration contract.
* Tests for relevant interface behavior.
* Instructions for running the frontend.

### Agent 2 — Multimodal AI and Model Integration

Responsibilities:

* Investigate supported Meta model capabilities.
* Verify access to the relevant APIs or SDKs.
* Implement the model integration.
* Define the visual input format.
* Implement frame sampling or other appropriate input processing.
* Develop structured event-assessment outputs.
* Handle API failures, invalid responses, timeouts, and rate limits.
* Keep credentials server-side.
* Document actual model limitations.

The model should return a predictable schema rather than unrestricted prose.

Proposed output structure:

{
"timestamp": "ISO-8601 timestamp",
"observations": [
{
"action": "observable action",
"evidence": "description of the visual evidence",
"confidence": 0.0
}
],
"event_type": "event category or unknown",
"assessment": "brief explanation",
"uncertainty": "what cannot be determined from the evidence",
"requires_human_review": true
}

This is an initial contract, not an excuse to invent calibrated confidence scores. Revise it to match what the underlying model can reliably support.

Deliverables:

* Working model integration.
* Input and output schema.
* Documented setup and configuration.
* Tests using representative inputs.
* Evidence that the integration calls the real model.

### Agent 3 — Detection Pipeline and Evaluation

Responsibilities:

* Define the event categories.
* Create the test protocol.
* Build the scenario evaluation dataset.
* Implement the event-processing pipeline.
* Record predictions and ground-truth labels.
* Calculate false positives, false negatives, precision, recall, and other appropriate metrics.
* Identify common model failures.
* Compare the complete system against a simpler baseline.
* Produce an evaluation report.

Initial test categories:

1. Ordinary movement.
2. Dancing or energetic movement.
3. Arm waving or ambiguous gestures.
4. Staged physical altercation.
5. A person falling or deliberately lowering themselves.
6. Visually similar actions that should not trigger the same alert.
7. Poor lighting, occlusion, or other challenging conditions where feasible.

Do not treat a single successful example as proof of reliability.

Use repeated trials and define ground-truth labels before examining the predictions whenever possible.

Distinguish between:

* An observation.
* An event classification.
* A system alert.
* A verified real-world incident.

These are not interchangeable.

Deliverables:

* Reproducible evaluation procedure.
* Scenario dataset or test manifest.
* Metric calculations.
* Failure-case report.
* Baseline comparison.

### Agent 4 — Integration, Reliability, and Demonstration

Responsibilities:

* Establish the shared architecture and integration contracts.
* Review the other agents' work.
* Integrate the frontend, backend, and model pipeline.
* Resolve incompatible assumptions and interfaces.
* Ensure the complete application runs end to end.
* Add meaningful automated tests.
* Verify error handling.
* Prepare the three-minute hackathon demonstration.
* Maintain a short list of remaining blockers.

The integration agent must not merely read the other agents' completion messages and assume the work is done.

It must run the software, inspect actual outputs, execute tests, and verify the complete workflow.

Deliverables:

* Integrated application.
* Passing test results for the critical path.
* Reproducible startup instructions.
* Demonstration script.
* Backup demonstration plan.
* Final list of verified capabilities and known limitations.

### My role as project lead

I will make final product decisions, provide credentials and access where necessary, test the system, and make decisions when trade-offs arise.

Agents should work independently where possible, but must not invent new product requirements, change shared interfaces without coordination, or overwrite each other's work.

## 6. ARCHITECTURE AND ENGINEERING RULES

Before implementation, establish the minimum viable architecture.

A possible structure is:

Camera input → Frame selection → Visual processing → Event assessment → Structured result → User interface → Evaluation log.

Adapt this to the actual framework and available model interfaces.

Engineering requirements:

* Real functionality, not mock implementations.
* No fake API responses presented as genuine model output.
* No placeholder functions on the critical execution path.
* No hardcoded successful test results.
* No claims that tests passed unless they were executed.
* No silent swallowing of exceptions.
* No secrets committed to source control.
* No unnecessary dependencies.
* No duplicate implementations of the same subsystem.
* No unbounded polling or uncontrolled model requests.
* No claim of continuous real-time analysis if the system processes occasional sampled frames.
* No unnecessary collection or storage of camera footage.
* No external CCTV integration for the initial prototype.

If the application analyzes frames periodically rather than processing a continuous stream, clearly disclose the sampling interval and resulting limitations.

Prefer processing on-device when feasible, but do not compromise the prototype's functionality merely to claim on-device processing.

Provide a visible indication when the camera is active. Handle camera permissions correctly, and minimize retention of sensitive footage.

## 7. EVALUATION AND PROOF

The submission must demonstrate what the system actually does.

Define a fixed test suite containing both positive and negative examples.

For every scenario, record:

* Scenario ID.
* Expected observable action.
* Ground-truth event label.
* Actual system output.
* Whether an alert was generated.
* Whether the alert was correct.
* Relevant visual evidence.
* Processing latency.
* Any error or failure.

Calculate metrics that are appropriate for the test design.

At minimum, investigate:

* Precision.
* Recall.
* False-positive rate.
* False-negative rate.
* End-to-end latency.

Report sample sizes and explain the limitations of the test.

Do not use model-reported confidence as a substitute for measured accuracy.

If a baseline is feasible, compare our pipeline against the same underlying model with a simpler prompt or processing approach. Keep the test cases consistent.

The purpose is to determine whether the additional pipeline, visual processing, or structured reasoning improves performance enough to justify its complexity.

A failure analysis is mandatory. Show at least one example where the system makes a mistake, if such an example occurs, and explain what the system cannot reliably determine.

## 8. THREE-MINUTE DEMONSTRATION

The final demonstration must be short, reproducible, and based on real outputs.

Proposed structure:

0:00–0:25 — Problem and objective

Explain that visual systems can misinterpret ordinary behavior and that the prototype investigates how to turn visual observations into reviewable event assessments.

0:25–0:55 — Live application

Open Meta Sentinel and demonstrate the real camera interface. Show the system receiving and processing visual input.

0:55–1:40 — Scenario testing

Perform ordinary movements and staged actions. Show the resulting observations, timestamps, uncertainty, and any alerts.

1:40–2:20 — Technical depth

Explain the actual roles of the integrated Meta AI technologies. Show the evidence-processing pipeline and a real structured model response.

2:20–2:45 — Evaluation

Present measured results from the test suite, including false positives and missed events where applicable.

2:45–3:00 — Conclusion

Explain the demonstrated capability, current limitations, and what would be required before real-world deployment.

Adapt the timing once the actual application is working. Do not promise functionality that has not been implemented.

## 9. SAFETY AND PRODUCT SCOPE

The initial product is an experimental visual event-analysis prototype, not an operational law-enforcement decision system.

Use consenting participants and staged scenarios.

Do not claim that a model can reliably infer criminal intent, determine guilt, or establish that a crime occurred based on body movements alone.

The initial system must not automatically contact police, dispatch emergency services, or take consequential action against a person.

Avoid face recognition, identity inference, and unnecessary biometric processing.

The output should help a human understand the visual evidence, not replace human judgment.

The same architecture may later support other applications, such as smoke detection, but do not expand into multiple complete products until the initial use case works.

## 10. EXECUTION PLAN

We have limited time. Do not spend the majority of the remaining schedule writing specifications.

Start with a short technical discovery phase.

Phase 1 — Verify and establish the foundation

* Confirm the repository state.
* Identify the existing language, framework, package manager, and deployment environment.
* Verify available Meta AI tools and access.
* Select the simplest feasible architecture.
* Define the shared input/output contracts.
* Assign the four agents their tasks.

Phase 2 — Prove the critical path

* Get one real visual input into the system.
* Process it through the actual model or supported vision pipeline.
* Return a structured assessment.
* Display the assessment in the interface.
* Verify the complete flow manually.

This is the first major milestone. Do not expand the scope before it works.

Phase 3 — Build the test suite

* Add the initial scenarios.
* Record expected outcomes.
* Run repeated tests.
* Calculate metrics.
* Identify failure cases.
* Compare with a simpler baseline if feasible.

Phase 4 — Integrate and harden

* Resolve bugs.
* Test permissions and failure states.
* Verify latency and request limits.
* Test on the intended demonstration device.
* Remove fake functionality and unused code.
* Run end-to-end tests.

Phase 5 — Submission and demonstration

* Freeze major features before the deadline.
* Rehearse the demo.
* Prepare a backup using previously captured, consented test footage if the live camera or network fails.
* Document the architecture, Meta AI integrations, evaluation results, and limitations.
* Verify the final submission requirements and deadline.

Set concrete checkpoints after the initial repository and API inspection. Work backward from the deadline, reserving time for integration and demo rehearsal.

## 11. DECISION-MAKING RULES

You are expected to exercise engineering judgment.

If the proposed design is technically unsound, identify the specific problem and recommend a better approach.

If a Meta AI product does not support the required input format, do not build a fake adapter. Find a supported route or reduce the scope.

If a component does not contribute measurable value, remove it.

If a feature cannot be completed reliably before the deadline, defer it.

If multiple architectural options are available, select the one that provides the strongest working demonstration with the least unnecessary complexity.

Do not confuse a large codebase with technical depth. Technical depth comes from solving a difficult problem, integrating the system correctly, and demonstrating measured results.

Do not spend time making generic claims about novelty. Investigate related work and existing solutions once the core technical approach is understood. Clearly identify what, if anything, is different about our implementation.

## 12. YOUR FIRST RESPONSE TO THIS BRIEF

Do not immediately generate the entire application.

First, return:

1. A concise summary of what Meta Sentinel is intended to demonstrate.
2. The actual state of the repository, based on inspection.
3. The relevant Meta AI APIs, models, and SDKs that are verifiably available.
4. The recommended architecture and why it is feasible.
5. The exact responsibilities and interface contracts for all four agents.
6. The critical technical risks, especially video input, model latency, API access, and event-classification reliability.
7. The first end-to-end milestone and the concrete acceptance criteria that prove it works.
8. A deadline-driven execution plan ending before November 4, 2026, at 9:00 PM Eastern.

Then begin execution.

Do not wait for unnecessary approval to perform reversible engineering work. Ask for clarification or credentials only when genuinely required.

Most importantly, distinguish what you have verified from what you are proposing. Never claim that code, integrations, tests, or capabilities exist until you have confirmed them.

Primary objective: Build a functioning Meta Sentinel prototype that demonstrates real visual event analysis, uses Meta AI tooling meaningfully, and produces measurable evidence of its capabilities and limitations.
