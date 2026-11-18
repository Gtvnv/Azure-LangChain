# Requirements Document

## Introduction

The Pytest Test Generator Agent is a Python command-line tool that receives Python source code (a file or a snippet) and uses LangChain with Azure OpenAI to generate a pytest test file named `test_<name>.py`. The generated file starts with `import pytest` and contains `def test_*` functions covering success and failure cases. The project is personal and educational, published as a public GitHub repository. It includes usage examples (at least two simple functions), a `.env.example` file with Azure OpenAI variables, and a README written in Brazilian Portuguese with step-by-step instructions and safety notes.

## Glossary

- **Agent**: The Python application that receives source code and produces a pytest test file using LangChain and Azure OpenAI.
- **CLI**: The command-line interface through which the user invokes the Agent.
- **LLM_Client**: The component that calls the Azure OpenAI chat deployment through LangChain.
- **Config_Loader**: The component that reads Azure OpenAI settings from environment variables and the `.env` file.
- **Source_Input**: Python source code supplied by the user as a file path or as a text snippet.
- **Test_File**: The generated Python file named `test_<name>.py`, where `<name>` is the base name of the Source_Input file or a user-provided name for a snippet.
- **Output_Validator**: The component that checks that generated content is valid pure Python and meets the Test_File format rules.
- **Output_Directory**: The directory where the Agent writes the Test_File. The default is `generated_tests/`.
- **Examples**: The directory `examples/` containing user-created sample functions and their generated tests.
- **README**: The `README.md` file at the repository root, written in Brazilian Portuguese.
- **Env_Template**: The `.env.example` file listing the required Azure OpenAI variables with placeholder values.
- **Repository**: The public GitHub repository that contains the Agent, Examples, README, Env_Template and `.gitignore`.
- **Success_Case**: A test scenario in which the function under test receives valid input and returns the expected result.
- **Failure_Case**: A test scenario in which the function under test receives invalid input and raises an exception or returns an error result.
- **Collection_Check**: The validation step that writes the generated content and the Source_Input module to a temporary directory and runs `pytest --collect-only` on that directory in a separate process, to detect broken imports without executing any test.
- **CI_Workflow**: The GitHub Actions workflow defined in `.github/workflows/ci.yml`.
- **Forbidden_Names_Secret**: The GitHub Actions secret named `FORBIDDEN_NAMES`, whose value is the repository owner's list of forbidden names, one per line.

## Requirements

### Requirement 1: Receive Python source input

**User Story:** As a developer, I want to give the Agent a Python file or snippet, so that it can generate tests for my code.

#### Acceptance Criteria

1. WHEN the user passes a path to an existing `.py` file to the CLI, THE Agent SHALL read the file content as UTF-8 text and use it as the Source_Input.
2. WHEN the user passes a code snippet through the CLI snippet option, THE Agent SHALL use the snippet text as the Source_Input.
3. WHEN the user passes a snippet through standard input and does not pass a file path or the CLI snippet option, THE Agent SHALL read standard input until end-of-file and use the text as the Source_Input.
4. IF the given file path does not exist, THEN THE CLI SHALL print an error message in Portuguese naming the missing path, exit with a non-zero status code, and not call the LLM_Client.
5. IF the Source_Input is empty or contains only whitespace, THEN THE CLI SHALL print an error message in Portuguese indicating the input is empty, exit with a non-zero status code, and not call the LLM_Client.
6. IF the Source_Input is not syntactically valid Python, THEN THE CLI SHALL print the syntax error with its line number, exit with a non-zero status code, and not call the LLM_Client.
7. IF the given file path exists but cannot be read as UTF-8 text (permission denied, path is a directory, or invalid UTF-8 bytes), THEN THE CLI SHALL print an error message in Portuguese naming the path and the failure reason, exit with a non-zero status code, and not call the LLM_Client.
8. IF the user passes more than one input source among file path, CLI snippet option, and standard input content, THEN THE CLI SHALL print an error message in Portuguese indicating that only one input source is allowed, exit with a non-zero status code, and not call the LLM_Client.

### Requirement 2: Generate tests with LangChain and Azure OpenAI

**User Story:** As a developer, I want the Agent to use an LLM to write the tests, so that I get meaningful test cases without writing them by hand.

#### Acceptance Criteria

1. WHEN a valid Source_Input is received, THE LLM_Client SHALL send the Source_Input to an Azure OpenAI chat deployment through LangChain using a prompt that instructs the model to generate pytest tests.
2. THE prompt SHALL instruct the model to produce at least one Success_Case and at least one Failure_Case for each public function in the Source_Input, where a public function is a module-level function whose name does not start with an underscore.
3. THE prompt SHALL instruct the model to return only Python code, with no Markdown fences (no line starting with three backticks) and no text outside Python code or Python comments.
4. THE prompt SHALL instruct the model to import the code under test from a module whose name equals the Source_Input file name without its extension.
5. THE LLM_Client SHALL use a temperature of 0 by default.
6. IF the Azure OpenAI call fails because of an authentication error, a network error or a quota error, THEN THE CLI SHALL print a Portuguese error message that names which of the three categories occurred, write no test file, and exit with a non-zero status code.
7. IF the Azure OpenAI call does not complete within 60 seconds, THEN THE LLM_Client SHALL abort the call, AND THE CLI SHALL print a Portuguese timeout message that states the 60-second limit, write no test file, and exit with a non-zero status code.
8. IF the Azure OpenAI call succeeds but the response is empty or contains only whitespace, THEN THE CLI SHALL print a Portuguese error message indicating that the model returned no content, write no test file, and exit with a non-zero status code.

### Requirement 3: Produce a valid Test_File

**User Story:** As a developer, I want the output to be a ready-to-run pytest file, so that I can execute it immediately.

#### Acceptance Criteria

1. WHEN the Agent submits generated content for validation, THE Output_Validator SHALL accept the content only if the first line, with no leading whitespace or blank lines before it, is exactly `import pytest`.
2. WHEN the Agent submits generated content for validation, THE Output_Validator SHALL accept the content only if it contains at least one top-level function, or one method of a top-level class, whose name starts with `test_`.
3. WHEN the Agent submits generated content for validation, THE Output_Validator SHALL accept the content only if it parses as valid Python source without syntax errors.
4. WHEN the model response contains Markdown code fences, THE Agent SHALL extract only the text inside the first fenced block, excluding the fence lines and the language tag, before validation.
5. WHEN the model response contains non-code text before the line `import pytest`, THE Agent SHALL remove all text before that line before validation.
6. WHEN the generated content passes validation, THE Agent SHALL write it to the Output_Directory as `test_<name>.py` using UTF-8 encoding, subject to the overwrite rules of Requirement 4.
7. IF the generated content fails validation, THEN THE Agent SHALL send the validation error to the LLM_Client, request a corrected version, and re-validate each response, for a maximum of 2 retries (3 attempts in total including the first).
8. IF the generated content still fails validation after 2 retries, THEN THE CLI SHALL print an error message that includes the last validation error, SHALL NOT create or modify any Test_File, and SHALL exit with a non-zero status code.
9. WHEN the Agent submits generated content for validation, THE Output_Validator SHALL accept the content only if it contains at least one test that asserts a Failure_Case using `pytest.raises`, `pytest.warns`, or `pytest.fail`.
10. FOR ALL valid generated contents, validating the content, writing it to disk and reading it back as UTF-8 SHALL produce text identical, character for character, to the validated content (round-trip property).
11. WHEN the Agent submits generated content for validation together with the module name, THE Output_Validator SHALL accept the content only if it contains at least one top-level statement of the form `from <module_name> import <names>`, where `<module_name>` equals the module name of the Source_Input.
12. WHEN generated content passes the checks of criteria 1, 2, 3, 9 and 11, THE Agent SHALL run the Collection_Check on it, with the Source_Input available as module `<module_name>` in the temporary directory, and SHALL accept the content only if `pytest --collect-only` exits with status code 0.
13. IF the Collection_Check fails, THEN THE Agent SHALL treat the failure as a validation error, send the last 20 lines of the pytest output (at most 2000 characters) to the LLM_Client together with the request for a corrected version, and count the attempt within the 2 retries defined in criterion 7.
14. IF the Collection_Check does not finish within 30 seconds, THEN THE Agent SHALL stop the pytest process, treat the timeout as a validation error that states the 30-second limit, and count the attempt within the 2 retries defined in criterion 7.
15. THE Collection_Check SHALL run with zero outbound network connections, with no `AZURE_OPENAI_*` variable in the environment of the pytest process, and with the working directory set to the temporary directory.
16. WHEN the Collection_Check ends, THE Agent SHALL remove the temporary directory and SHALL NOT create or modify any file outside it.

### Requirement 4: Control output location and name

**User Story:** As a developer, I want to control where the test file is written, so that it fits my project layout.

#### Acceptance Criteria

1. WHEN the Source_Input is a file named `<name>.py`, THE Agent SHALL name the Test_File `test_<name>.py`.
2. WHEN the Source_Input is a snippet and the user provides a module name option, THE Agent SHALL name the Test_File `test_<module name>.py`.
3. IF the Source_Input is a snippet and no module name is given, THEN THE CLI SHALL print an error message in Portuguese indicating that the module name is required, exit with a non-zero status code, and not create any Test_File.
4. IF the module name is not a valid Python identifier (letters, digits and underscores only, not starting with a digit, 1 to 100 characters), THEN THE CLI SHALL print an error message in Portuguese indicating that the module name is invalid, exit with a non-zero status code, and not create any Test_File.
5. WHERE the user provides an output directory option, THE Agent SHALL write the Test_File to that directory.
6. WHERE the user does not provide an output directory option, THE Agent SHALL write the Test_File to the Output_Directory default `generated_tests/`.
7. IF the Output_Directory does not exist, THEN THE Agent SHALL create it, including any missing parent directories, before writing the Test_File.
8. IF the Output_Directory cannot be created or written to, THEN THE CLI SHALL print an error message in Portuguese indicating the directory path and the failure, exit with a non-zero status code, and not create any Test_File.
9. IF a Test_File with the same name already exists in the Output_Directory and the user does not provide the force option, THEN THE CLI SHALL ask for confirmation before overwriting it, and SHALL leave the existing file unchanged unless the user confirms.
10. WHERE the user provides the force option, THE CLI SHALL overwrite an existing Test_File without asking for confirmation.
11. WHEN the Test_File is written, THE CLI SHALL print the path of the written file and exit with status code zero.
12. IF a Test_File with the same name already exists, the user does not provide the force option, and no interactive input is available (no TTY, closed or piped standard input, or CI pipeline), THEN THE CLI SHALL treat the missing confirmation as a refusal, leave the existing file unchanged, print an error message in Portuguese indicating that the file exists and that the force option is required, and exit with a non-zero status code.

### Requirement 5: Configure Azure OpenAI through environment variables

**User Story:** As a developer, I want to configure credentials through environment variables, so that secrets stay out of the source code.

#### Acceptance Criteria

1. THE Config_Loader SHALL read the variables `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_VERSION` and `AZURE_OPENAI_DEPLOYMENT_NAME` from the process environment.
2. WHEN the CLI starts and a `.env` file exists in the current working directory, THE Config_Loader SHALL load the variables defined in that file before reading the process environment.
3. IF a variable defined in the `.env` file is also set in the process environment, THEN THE Config_Loader SHALL keep the value from the process environment.
4. IF a required variable from criterion 1 is missing, is empty, or contains only whitespace, THEN THE CLI SHALL print a Portuguese message that lists every such variable name and names the Env_Template file, exit with status code 1, and make zero calls to the LLM_Client.
5. THE Env_Template SHALL list the four variables from criterion 1, one per line, each with a placeholder value that is not a real credential and a Portuguese comment describing the variable.
6. THE Agent SHALL NOT include the value of `AZURE_OPENAI_API_KEY`, in full or in part, in any standard output, standard error, log entry or error message.
7. THE Repository SHALL include a `.gitignore` that excludes `.env`, virtual environment directories, `__pycache__` directories, `.pytest_cache` directories and the `generated_tests/` directory.

### Requirement 6: Provide usage examples

**User Story:** As a learner, I want working examples, so that I can see the Agent producing tests that pass.

#### Acceptance Criteria

1. THE Examples SHALL contain at least two example Python modules, each containing at least one function with a documented signature, and together containing at least three functions (for example `add`, `subtract` and `divide`).
2. THE Examples SHALL include `divide` or an equivalent function that raises a ValueError (or a documented built-in exception type) when called with invalid input (for example a divisor of zero), so that a Failure_Case is demonstrable.
3. THE Examples SHALL contain, for each example module, exactly one committed Test_File generated by the Agent, containing at least one test per function in that module and at least one test that asserts the exception for the Failure_Case function.
4. WHEN the user runs `pytest` from the repository root, THE Examples SHALL execute all committed Test_Files, and the run SHALL finish with exit code 0, zero failed tests and zero errored tests.
5. THE Repository SHALL configure pytest, through `pytest.ini` or `pyproject.toml`, so that WHEN `pytest` is run from the repository root, the Test_Files import the example modules without the user setting `PYTHONPATH`, editing `sys.path` or changing the working directory.
6. THE README SHALL show, for each example module, the exact command line used to generate its Test_File (including the module path argument), so that running that command from the repository root produces a Test_File at the committed location.
7. IF the user runs the README generation command for an example module whose Test_File already exists, THEN THE Agent SHALL report to the user that the file exists and SHALL leave the existing committed Test_File content unchanged unless the user confirms overwriting.

### Requirement 7: Document the project in the README

**User Story:** As a visitor of the public repository, I want a clear README in Portuguese, so that I can understand and run the project.

#### Acceptance Criteria

1. THE README SHALL be written in Brazilian Portuguese (pt-BR), with section headings, instructions and notes in that language, AND THE README SHALL contain no complete paragraph written in another language, except for code, commands, file names, environment variable names and proper names of technologies; both conditions SHALL hold for the README to be compliant.
2. THE README SHALL contain one heading for each of these 12 sections: project description, features, architecture overview, prerequisites, installation, environment variable configuration, how to run the Agent, usage examples, how to run the tests with `pytest`, project structure, safety notes and license.
3. THE README SHALL contain a numbered, step-by-step sequence that covers, in this order: creating a virtual environment, activating it, installing dependencies from `requirements.txt`, and copying the Env_Template file to `.env`, with the exact command for each step for both Windows (PowerShell) and Linux/macOS (bash).
4. THE README SHALL list every Azure OpenAI variable defined in the Env_Template and, for each one, state its purpose and the name of the Azure portal page or field where its value is found.
5. THE README SHALL contain a safety note stating that the user must never commit `.env` or any secret (API keys, endpoints with keys, tokens), and that `.env` must be listed in `.gitignore`.
6. THE README SHALL contain a safety note stating that the generated tests are produced by an LLM, that they may be incorrect or unsafe, and that the user must review the generated code before executing it.
7. WHERE screenshots exist, THE README SHALL reference each one with a Markdown image link whose relative path points to a file that exists in the `images/` folder, and each image SHALL have non-empty alternative text.
8. THE Repository SHALL NOT contain, in the README, source code, comments, documentation or any file prepared for commit, the name of any bootcamp or course platform, verified by a case-insensitive text search over all tracked and commit-ready files that returns zero matches for a list of such names defined by the repository owner.
9. IF a file prepared for commit contains the name of a bootcamp or course platform, THEN THE Repository SHALL be considered non-compliant with criterion 8 and the occurrence SHALL be removed before the commit is made.

### Requirement 8: Manage dependencies and project structure

**User Story:** As a developer, I want a clean, reproducible project setup, so that anyone can install and run it.

#### Acceptance Criteria

1. THE Repository SHALL include a `requirements.txt` file at the repository root that lists `langchain`, `langchain-openai`, `python-dotenv`, `pytest` and `hypothesis`, each on its own line, and each with a compatible version range (an inclusive lower bound equal to the version installed when this requirement was updated and an exclusive upper bound at the next major version), namely: `langchain>=1.5.0,<2`, `langchain-openai>=1.8.1,<2`, `python-dotenv>=1.2.4,<2`, `pytest>=9.2.0,<10` and `hypothesis>=6.170.15,<7`.
2. WHEN a user runs `pip install -r requirements.txt` in a clean Python virtual environment, THE Repository SHALL complete the installation with exit code 0 and make `langchain`, `langchain_openai`, `dotenv` and `pytest` importable.
3. THE Repository SHALL place the Agent code in a dedicated package directory that contains no Example files, and SHALL place the Examples in a separate directory outside that package.
4. WHEN the user runs the entry point with `python -m <package>` or `python <script>.py` and the arguments described in Requirement 1 and Requirement 4, THE CLI SHALL execute the same behavior as described in those requirements.
5. THE Agent SHALL implement configuration loading, prompt construction, LLM calling and output validation as four separate functions or modules, where each one has a single responsibility and can be imported and tested without invoking the other three.
6. WHEN the user passes the `--help` or `-h` option, THE CLI SHALL print usage instructions in Portuguese that list every supported argument with a description, and SHALL exit with code 0 without calling the LLM.
7. IF the user passes an unknown argument or omits a required argument, THEN THE CLI SHALL print an error message in Portuguese indicating the problem, print the usage instructions, and exit with a non-zero code without calling the LLM.
8. IF the user passes an abbreviation of a long option (for example `--forc` for `--force`, or `--out` for `--output-dir`), THEN THE CLI SHALL reject it as an unknown argument, print an error message in Portuguese that names the rejected argument, print the usage instructions, exit with status code 2, and make zero calls to the LLM_Client.
9. WHEN the user passes a long option with its full name, THE CLI SHALL accept it and run the behavior described in Requirement 1 and Requirement 4.

### Requirement 9: Test the Agent itself

**User Story:** As a maintainer, I want automated tests for the Agent's own logic, so that regressions are detected without calling Azure.

#### Acceptance Criteria

1. THE Repository SHALL include unit tests that cover, for each of the Config_Loader, the Output_Validator, the fence-removal logic and the output file naming logic, at least one passing-input case and at least one failing-input or boundary case.
2. THE unit tests SHALL replace the LLM_Client with a fake so that the tests run with zero outbound network connections and with no Azure credential environment variables set.
3. THE unit tests SHALL verify the retry behavior of Requirement 3 criteria 7 and 8 using a fake LLM_Client that returns invalid content. The tests SHALL assert the exact number of LLM_Client calls made, and the final outcome after the maximum number of attempts defined in Requirement 3 is reached.
4. FOR ALL strings produced by wrapping valid Python code in Markdown fences, removing the fences SHALL return the original code (round-trip property). The property test SHALL run at least 100 generated examples.
5. FOR ALL cleaned contents, applying the fence-removal logic a second time SHALL return content identical to the first result (idempotence property). The property test SHALL run at least 100 generated examples.
6. WHEN the user runs `pytest` from the repository root with no Azure credential environment variables set and no network access, THE unit tests SHALL pass with exit code 0 and with zero failed, errored or skipped tests.
7. IF a unit test attempts to open a network connection to a real Azure endpoint, THEN THE unit tests SHALL fail that test with an error indicating that network access is not allowed.
8. THE Agent SHALL accept the Collection_Check as an injectable function, so that unit tests replace the pytest subprocess with a fake and run the generation loop with zero subprocesses.
9. THE unit tests SHALL verify the Collection_Check against a real pytest subprocess in at least one passing case (valid import) and one failing case (import of a name or module that does not exist), using only a temporary directory and no network.

### Requirement 10: Run continuous integration on GitHub Actions

**User Story:** As a maintainer, I want every push and pull request checked automatically, so that regressions are detected before merging.

#### Acceptance Criteria

1. THE Repository SHALL include the CI_Workflow at `.github/workflows/ci.yml`.
2. WHEN a push to any branch or a pull request is made, THE CI_Workflow SHALL start one job on an Ubuntu runner with Python 3.12.
3. WHEN the job starts, THE CI_Workflow SHALL install the dependencies with `pip install -r requirements.txt`.
4. WHEN the dependencies are installed, THE CI_Workflow SHALL run `python -m pytest` from the repository root with no `AZURE_OPENAI_*` variable defined in the job, the steps or the secrets passed to them.
5. IF `python -m pytest` exits with a non-zero status code, THEN THE CI_Workflow SHALL end with a failed status.
6. WHERE the Forbidden_Names_Secret is configured, THE CI_Workflow SHALL write its value to a file in the runner temporary directory, set `FORBIDDEN_NAMES_FILE` to that path and run `python scripts/check_forbidden_names.py`.
7. IF the Forbidden_Names_Secret is not configured (empty or unavailable, for example in a pull request from a fork), THEN THE CI_Workflow SHALL skip the forbidden names step and SHALL NOT fail because of the skipped step.
8. THE CI_Workflow SHALL request only the `contents: read` permission and SHALL NOT print the value of the Forbidden_Names_Secret in any log line.