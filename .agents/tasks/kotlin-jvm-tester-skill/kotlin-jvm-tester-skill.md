# Task: Kotlin JVM Tester Skill

We need to have a skill which will supplement `kotlin-engineer` and `raise-coverage` skills with
the ability to write tests in Kotlin for both Java and Kotlin code.

## Subtasks known at the moment
- Take the documents gathered under the `agents/tasks/kotlin-jvm-testser-skill/` directory and
  use them as the input for the task creation. These documents are memory items that were collected as
  the result of the `increase-coverage` skill run by Junie on the Gemini 3 Flash model. 
  We will use other agents and models in the future, so the skill should be cross-agent as much as possible.

- Analyze the testing practices in the selected subprojects under the SpineEventEngine organization:
  - https://github.com/SpineEventEngine/base-libraries
  - https://github.com/SpineEventEngine/core-jvm
  - https://github.com/SpineEventEngine/compiler
  - https://github.com/SpineEventEngine/validation
  - https://github.com/SpineEventEngine/core-jvm-compiler
  and use this code as the input for formulating guidelines and requirements for the skill.
  
- Compose the skill knowing that:
  1. Our codebase is mixed Java/Kotlin, and we have tests written in both languages.
  2. A large portion of the tests are still written in Java.
  3. We are going to migrate all the code to Kotlin eventually, 
     so the skill should be focused on Kotlin testing practices.
  4. When we need to write more tests for the existing Java code or Kotlin 
     (e.g `raise-coverage` or `kotlin-engineer` skill) we will
     use ONLY Kotlin for writing new tests. 
     We want to minimise the conversion work in the future.
  Possible scenarios for testing existing Java code are described in the section 
  "Adding new tests for existing Java code" below.

## Adding new tests for existing Java code
  
When we need to add new tests for the existing Java code, we have the following situations in our codebase:

1. There are no tests for the code in question.  
   Action: create a new Kotlin test suite for the code in question.

2. There are test suites already written in Kotlin. 
   Action: add new tests to the existing Kotlin test suite.

3. There are test suites already written in Java. 
   No test suites are writting in Kotlin for the code in question.
   Actions:
   3.1 Create a new test suite in Kotlin. Name selection:
     - If the Java test suites is named `XTest`, name the new Kotlin test suite must be named `XSpec`.
     - If the Java test suite already has the `Spec` suffix (`XSpec`, name the Kotlin test suite as `XKtSpec`
   3.2. Document the new Kotlin test suite
     - Explain in the KDoc of the new Kotlin test suite that it is a supplement to the existing Java test
       suite and that it should be used for writing new tests for the existing Java code.
     - Have the link to the existing Java test suite in the KDoc of the new Kotlin test suite for
       easy navigation between the two test suites.
                                                                   
