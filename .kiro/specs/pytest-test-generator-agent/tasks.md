# Implementation Plan: Pytest Test Generator Agent

## Overview

The design uses Python, so all tasks are written in Python. The plan builds the pure core first (input, config, validator, prompt, LLM client, generator, writer), then wires everything in the CLI, and finally adds the examples, README and repository checks. Each property from the design is its own optional test sub-task placed right after the code it checks. Property tests use Hypothesis and each carries the tag `# Feature: pytest-test-generator-agent, Property N: <title>`.

## Tasks

- [x] 1. Set up project structure and shared test infrastructure
  - [x] 1.1 Create the package skeleton, configuration files and test fixtures
    - Create `pytest_agent/__init__.py` and `pytest_agent/errors.py` with `AgentError` (with `exit_code`) and the subclasses `InputError`, `ConfigError`, `LlmError` (with `category`), `ValidationFailedError`, `OutputError`
    - Create `pyproject.toml` with `[tool.pytest.ini_options] pythonpath = [".", "examples"]` and `testpaths = ["tests", "examples"]`
    - Create `requirements.txt` with `langchain`, `langchain-openai`, `python-dotenv`, `pytest`, `hypothesis`, one per line
    - Create `.gitignore` excluding `.env`, virtual environments, `__pycache__`, `.pytest_cache` and the root-anchored `/generated_tests/`
    - Create `.env.example` with the four `AZURE_OPENAI_*` variables, placeholder values and a Portuguese comment on each
    - Create `tests/conftest.py` with the autouse `block_network` fixture (patches `socket.socket.connect` and `socket.create_connection` to raise `AssertionError("acesso à rede não permitido")`) and the autouse `clean_azure_env` fixture
    - Create `tests/fakes.py` with `FakeLlm(responses)` that records `calls`, repeats the last response, and a variant that raises a configured exception
    - _Requirements: 5.5, 5.7, 6.5, 8.1, 8.3, 9.2, 9.7_

- [x] 2. Implement input reading and validation
  - [x] 2.1 Implement `pytest_agent/input_reader.py`
    - `SourceInput`, `read_source`, `check_source`, `resolve_module_name`, `is_valid_module_name` (`^[A-Za-z_][A-Za-z0-9_]{0,99}$`)
    - Read files as UTF-8; map `FileNotFoundError`, `PermissionError`, `IsADirectoryError`, `UnicodeDecodeError` to `InputError` naming the path and reason
    - Reject empty or whitespace-only input, report `SyntaxError` with line number, reject multiple input sources, require a module name for snippet and stdin
    - Messages in Portuguese
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 4.2, 4.3, 4.4_

  - [x] 2.2 Write property test for UTF-8 file input round trip
    - File: `tests/test_prop_input_roundtrip.py`; use `tempfile` inside the test body
    - **Property 1: UTF-8 file input round trip**
    - **Validates: Requirements 1.1**

  - [x] 2.3 Write property test for blank input rejection
    - File: `tests/test_prop_blank_input.py`; covers `check_source` and the CLI with a blank snippet (zero LLM calls, non-zero exit)
    - **Property 2: Blank input is rejected before any LLM call**
    - **Validates: Requirements 1.5**

  - [x] 2.4 Write property test for module name validation
    - File: `tests/test_prop_module_name.py`; covers `is_valid_module_name` and the CLI creating no file for an invalid name
    - **Property 9: Module name validation matches the identifier rule**
    - **Validates: Requirements 4.4**

  - [x] 2.5 Write unit tests for input reading
    - File: `tests/test_input_reader.py`
    - File, snippet and stdin (`io.StringIO`) sources; missing path, directory path, invalid UTF-8 bytes, syntax error with line number, source conflicts, missing module name
    - _Requirements: 1.2, 1.3, 1.4, 1.6, 1.7, 1.8, 4.3_

- [x] 3. Implement configuration loading
  - [x] 3.1 Implement `pytest_agent/config.py`
    - `AzureConfig` (frozen dataclass, `api_key` with `repr=False`), `REQUIRED_VARS`, `load_config(env=None, dotenv_path=None)`
    - With `env=None`, call `load_dotenv(..., override=False)` on `Path.cwd()/".env"` and read `os.environ`; with a mapping, touch no file or global state
    - Collect every missing, empty or whitespace-only variable in declaration order into one `ConfigError` that mentions `.env.example`; never format the key into messages
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_

  - [x] 3.2 Write property test for config loading
    - File: `tests/test_prop_config_values.py`
    - **Property 10: Config loading returns the supplied values**
    - **Validates: Requirements 5.1**

  - [x] 3.3 Write property test for missing or blank variables
    - File: `tests/test_prop_config_missing.py`; also checks the CLI makes zero LLM calls and exits with status 1
    - **Property 11: Missing or blank variables are all reported**
    - **Validates: Requirements 5.4**

  - [x] 3.4 Write unit tests for config loading
    - File: `tests/test_config.py`
    - `.env` loading from `tmp_path`, process variable precedence over `.env`, `repr(config)` hides the key
    - _Requirements: 5.2, 5.3, 5.6_

- [x] 4. Implement the output validator
  - [x] 4.1 Implement `pytest_agent/validator.py`
    - `extract_code`: fenced block first (unclosed fence takes the rest), then trim everything before the first `import pytest` line, applied in that order so the function is idempotent
    - `ValidationResult` and `validate_test_content` with the four ordered checks: first line exactly `import pytest`, `ast.parse`, at least one `test_*` function or method, at least one `pytest.raises`/`pytest.warns`/`pytest.fail`
    - Error strings in Portuguese
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.9_

  - [x] 4.2 Write property test for validator acceptance
    - File: `tests/test_prop_validator.py`; `max_examples=200`
    - **Property 5: Validator accepts content exactly when all conditions hold**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.9**

  - [x] 4.3 Write property test for prose removal
    - File: `tests/test_prop_prose_removal.py`
    - **Property 6: Prose before the import line is removed**
    - **Validates: Requirements 3.5**

  - [x] 4.4 Write property test for fence wrapping round trip
    - File: `tests/test_prop_fence_roundtrip.py`; `max_examples=200`
    - **Property 13: Fence wrapping round trip**
    - **Validates: Requirements 3.4, 9.4**

  - [x] 4.5 Write property test for fence extraction idempotence
    - File: `tests/test_prop_fence_idempotent.py`; `max_examples=200`
    - **Property 14: Fence extraction is idempotent**
    - **Validates: Requirements 9.5**

  - [x] 4.6 Write unit tests for the validator
    - File: `tests/test_validator.py`
    - Passing and failing cases for each of the four checks, unclosed fence, language tag, no `import pytest` line
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.9, 9.1_

- [ ] 5. Implement prompt construction and the Azure LLM client
  - [x] 5.1 Implement `pytest_agent/prompt.py`
    - `Message` dataclass, `SYSTEM_PROMPT`, `build_messages(source_code, module_name)`, `build_retry_messages(previous, bad_output, error)`
    - The system prompt requires: pytest tests, start with `import pytest`, `from <module_name> import ...`, at least one success and one failure test per public module-level function, code only with no fences
    - Do not import LangChain in this module
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 3.7_

  - [x] 5.2 Write property test for prompt content
    - File: `tests/test_prop_prompt.py`
    - **Property 3: Prompt carries the source and module name**
    - **Validates: Requirements 2.1, 2.4**

  - [x] 5.3 Implement `pytest_agent/llm_client.py`
    - `LlmClient` protocol, `AzureLlmClient` with `from_config`, building `AzureChatOpenAI(... temperature=0, timeout=60, max_retries=0)` and converting `Message` to LangChain message types
    - Pure `map_exception(exc) -> LlmError` for authentication, timeout (message states the 60-second limit), network and quota categories; never echo raw SDK text or the API key
    - _Requirements: 2.1, 2.5, 2.6, 2.7, 5.6_

  - [x] 5.4 Write unit tests for prompt and LLM client
    - File: `tests/test_prompt_and_client.py`
    - Static prompt text assertions; patched `AzureChatOpenAI` receives `temperature=0`, `timeout=60`, `max_retries=0`; `map_exception` with synthetic auth, connection, timeout and rate-limit exceptions
    - _Requirements: 2.2, 2.3, 2.5, 2.6, 2.7_

- [ ] 6. Implement the generation orchestrator
  - [x] 6.1 Implement `pytest_agent/generator.py`
    - `MAX_RETRIES = 2` and `generate_tests(source_code, module_name, llm)`
    - Loop up to 3 attempts: call the LLM, raise `LlmError("vazio")` at once for a blank response, run `extract_code` and `validate_test_content`, on failure append retry messages
    - Raise `ValidationFailedError` with the last error after the final failure; let client `LlmError` propagate without retry
    - _Requirements: 2.8, 3.4, 3.5, 3.7, 3.8_

  - [x] 6.2 Write property test for blank model responses
    - File: `tests/test_prop_blank_response.py`; asserts exactly one LLM call and no file written
    - **Property 4: Blank model responses are treated as errors**
    - **Validates: Requirements 2.8**

  - [x] 6.3 Write unit tests for retry behavior
    - File: `tests/test_generator.py`
    - Always-invalid fake gives exactly 3 calls and `ValidationFailedError` with the last error; invalid twice then valid gives 3 calls and success; valid first gives 1 call
    - _Requirements: 3.7, 3.8, 9.3_

- [x] 7. Implement the file writer
  - [x] 7.1 Implement `pytest_agent/writer.py`
    - `build_test_file_name`, `resolve_target`, `check_overwrite(target, force, is_interactive, ask)`, `write_test_file`
    - `check_overwrite`: prompt `[s/N]`, accept only `s`/`sim` case-insensitive, treat `EOFError` or non-interactive as refusal with a message that requires `--force`
    - `write_test_file`: create parents, write a temp file in the same directory with UTF-8 and `newline=""`, `os.replace` onto the target, remove the temp file in `finally`, map `OSError` to `OutputError` naming the directory
    - _Requirements: 3.6, 3.10, 4.1, 4.2, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.12, 6.7_

  - [x] 7.2 Write property test for write and read-back
    - File: `tests/test_prop_write_roundtrip.py`; include non-ASCII text and both `\n` and `\r\n`
    - **Property 7: Written content reads back identically**
    - **Validates: Requirements 3.6, 3.10**

  - [x] 7.3 Write property test for test file naming
    - File: `tests/test_prop_file_naming.py`
    - **Property 8: Test file naming**
    - **Validates: Requirements 4.1, 4.2**

  - [x] 7.4 Write unit tests for the writer
    - File: `tests/test_writer.py`
    - Parent directory creation, default directory, output directory that is a file, overwrite answers `s`, `sim`, `n`, empty, EOF, `--force`, non-interactive refusal with existing file untouched
    - _Requirements: 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.12_

- [x] 8. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 9. Implement the CLI and wire the components
  - [x] 9.1 Implement `pytest_agent/cli.py` and `pytest_agent/__main__.py`
    - `PtArgumentParser` overriding `error()` to print a Portuguese message plus usage and exit with code 2; `build_parser` with `arquivo`, `--snippet`, `--module-name`, `--output-dir` (default `generated_tests/`), `--force` and Portuguese help
    - `main(argv, *, llm_factory, stdin, stdout, stderr)` running checks in order before any LLM call: single source, read, non-empty, `ast.parse`, module name, config, overwrite check
    - Then `generate_tests`, `write_test_file`, print the written path and return 0; catch `AgentError` (print to stderr, return its exit code) and `KeyboardInterrupt` (return 130)
    - Read stdin only when no file or snippet is given and stdin is not a TTY
    - `__main__.py` calls `main` so `python -m pytest_agent` works
    - _Requirements: 1.1, 1.2, 1.3, 1.8, 4.1, 4.2, 4.3, 4.5, 4.6, 4.9, 4.10, 4.11, 4.12, 5.4, 6.7, 8.4, 8.6, 8.7_

  - [x] 9.2 Write property test that the API key never appears in output
    - File: `tests/test_prop_no_key_leak.py`; run every failure path with `FakeLlm`, capture stdout, stderr, log records, exception messages and `repr(config)`
    - **Property 12: The API key never appears in output**
    - **Validates: Requirements 5.6**

  - [x] 9.3 Write property test for unknown arguments
    - File: `tests/test_prop_unknown_args.py`
    - **Property 15: Unknown arguments are rejected without an LLM call**
    - **Validates: Requirements 8.7**

  - [x] 9.4 Write unit tests for the CLI
    - File: `tests/test_cli.py`
    - `--help` in Portuguese with exit 0, missing arguments, success path prints the path and exits 0, network guard raises `AssertionError` on a socket connection
    - _Requirements: 4.11, 8.6, 8.7, 9.2, 9.7_

- [x] 10. Create the usage examples
  - [x] 10.1 Create example modules
    - `examples/calculadora.py` with `add` and `subtract`, `examples/divisao.py` with `divide` raising `ValueError` when the divisor is zero; type hints and docstrings
    - _Requirements: 6.1, 6.2_

  - [x] 10.2 Create the committed example test files
    - `examples/generated_tests/test_calculadora.py` and `examples/generated_tests/test_divisao.py` in the format the Agent produces: first line `import pytest`, imports from `calculadora` and `divisao`, success tests per function, and `pytest.raises(ValueError)` for `divide`
    - These can be regenerated later with the README commands after the owner reviews the output
    - _Requirements: 6.3, 6.4, 6.5_

- [x] 11. Write documentation and repository checks
  - [x] 11.1 Write the pt-BR `README.md`
    - The 12 required headings, numbered installation steps with PowerShell and bash commands (venv creation, activation, `pip install -r requirements.txt`, copy `.env.example` to `.env`)
    - Variable table with purpose and Azure portal location, generation commands `python -m pytest_agent examples/calculadora.py --output-dir examples/generated_tests` and the one for `examples/divisao.py`, the overwrite and `--force` behavior
    - Safety notes: never commit `.env` or secrets, and review LLM-generated tests before running them
    - Screenshot links only to existing files in `images/` with non-empty alt text
    - Do not mention any bootcamp or course platform
    - _Requirements: 6.6, 6.7, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8_

  - [x] 11.2 Create `scripts/check_forbidden_names.py`
    - Read the deny list path from the `FORBIDDEN_NAMES_FILE` environment variable (file kept outside the repository), scan tracked and commit-ready text files case-insensitively, exit non-zero on any match
    - The script must not contain any such name itself
    - _Requirements: 7.8, 7.9_

  - [x] 11.3 Write repository layout tests
    - File: `tests/test_repo_layout.py`
    - Check `requirements.txt` lines, `.gitignore` patterns including anchored `/generated_tests/`, `.env.example` format, `pyproject.toml` settings, example modules (at least 3 functions in 2 modules, `divide` raises `ValueError`), example tests cover every function and contain `pytest.raises`, README headings, commands, variable table, safety notes and image links
    - Check `pytest_agent/` contains no example files, each of the four core modules imports in a fresh subprocess without the other three, and `python -m pytest_agent --help` exits 0
    - _Requirements: 5.5, 5.7, 6.1, 6.2, 6.3, 6.5, 6.6, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 8.1, 8.3, 8.4, 8.5_

- [x] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. Reject abbreviations of long CLI options
  - [x] 13.1 Create the parser with `allow_abbrev=False`
    - In `pytest_agent/cli.py`, pass `allow_abbrev=False` when `PtArgumentParser` is built in `build_parser`
    - Make sure the Portuguese error message from `PtArgumentParser.error()` names the rejected token and still prints the usage and exits with code 2
    - Full option names (`--snippet`, `--module-name`, `--output-dir`, `--force`, `--help`) keep working
    - _Requirements: 8.7, 8.8, 8.9_

  - [x]* 13.2 Update the property test for unknown arguments
    - File: `tests/test_prop_unknown_args.py`
    - Extend the generator with proper prefixes of each supported long option (at least one character after `--`); assert exit code 2, the token in the Portuguese message, and zero LLM calls; also assert that each full option name is accepted
    - **Property 15: Unknown arguments and option abbreviations are rejected without an LLM call**
    - **Validates: Requirements 8.7, 8.8, 8.9**

  - [x]* 13.3 Add unit tests for abbreviations
    - File: `tests/test_cli.py`
    - `--forc`, `--out`, `--mod` and `--snippe` exit 2 with zero LLM calls; the full options still parse
    - _Requirements: 8.8, 8.9_

- [x] 14. Pin dependency version ranges
  - [x] 14.1 Update `requirements.txt`
    - One package per line: `langchain>=1.5.0,<2`, `langchain-openai>=1.8.1,<2`, `python-dotenv>=1.2.4,<2`, `pytest>=9.2.0,<10`, `hypothesis>=6.170.15,<7` (versions installed when the spec was updated, from `pip list`)
    - _Requirements: 8.1, 8.2_

  - [x]* 14.2 Adapt the layout test for `requirements.txt`
    - File: `tests/test_repo_layout.py`
    - Replace the whole-line comparison in `test_requirements_lists_required_packages_one_per_line` with a parse of each line: package name, `>=` lower bound and `<` exclusive upper bound; require the five packages, one per line, no duplicates
    - _Requirements: 8.1_

- [x] 15. Validate the target module import and pytest collection
  - [x] 15.1 Add `validate_module_import` to `pytest_agent/validator.py`
    - `validate_module_import(content, module_name) -> ValidationResult`: ok only if a top-level `ast.ImportFrom` with `level == 0` and `module == module_name` exists; Portuguese error naming the expected `from <module_name> import ...` line
    - Leave `validate_test_content` and `extract_code` unchanged so existing properties keep holding
    - _Requirements: 3.11_

  - [x]* 15.2 Write property test for the module import check
    - File: `tests/test_prop_module_import.py`
    - **Property 16: Module import check matches the top-level import rule**
    - **Validates: Requirements 3.11**

  - [x] 15.3 Implement `pytest_agent/collection_check.py`
    - `CollectionResult`, `Collector` type, `COLLECT_TIMEOUT_S = 30.0`, pure `build_collect_command`, `build_collect_env` (drops `AZURE_OPENAI_*`, sets `PYTHONDONTWRITEBYTECODE=1`) and `summarize_output` (last 20 lines, at most 2000 characters)
    - `collect_with_pytest(test_content, module_name, source_code, *, timeout_s, run=subprocess.run)`: temporary directory with `<module_name>.py`, `test_<module_name>.py` and an empty `pytest.ini`, run `python -m pytest --collect-only -q -p no:cacheprovider -c <ini> <test file>` with `cwd` in the temporary directory, map non-zero exit, `TimeoutExpired` (message states 30 s) and `OSError` to `ok=False`, remove the directory in `finally`
    - Do not import LangChain or the other agent modules except `errors` if needed
    - _Requirements: 3.12, 3.13, 3.14, 3.15, 3.16_

  - [x]* 15.4 Write property test for the output summary
    - File: `tests/test_prop_summarize_output.py`
    - **Property 18: Collector output summary is bounded**
    - **Validates: Requirements 3.13**

  - [x]* 15.5 Write unit tests for the collection check
    - File: `tests/test_collection_check.py`
    - Pure functions (`build_collect_command`, `build_collect_env`); fake `run` with a failed `CompletedProcess`, `TimeoutExpired` and `OSError`; two real-subprocess tests (valid import returns ok; import of a missing name returns not ok with the error in the output); the temporary directory is gone afterwards
    - _Requirements: 3.12, 3.13, 3.14, 3.15, 3.16, 9.9_

  - [x] 15.6 Integrate the checks into the generator and the CLI
    - `pytest_agent/generator.py`: add `collector: Collector = collect_with_pytest` to `generate_tests`; after `validate_test_content` run `validate_module_import`, then `collector(content, module_name, source_code)`; failures (including `CollectionResult.output`) feed `build_retry_messages` inside the existing `MAX_RETRIES` loop
    - `pytest_agent/cli.py`: add a `collector` parameter to `main` and pass it to `generate_tests`
    - `tests/fakes.py`: add `ok_collector`; update the existing generator and CLI tests (and `tests/test_prop_blank_response.py`, `tests/test_prop_no_key_leak.py`) to inject it so they start no subprocess; keep their assertions unchanged
    - _Requirements: 3.7, 3.8, 3.11, 3.12, 3.13, 9.8_

  - [x]* 15.7 Write property test for collection failures in the retry loop
    - File: `tests/test_prop_collection_retry.py`
    - Use `FakeLlm` and fake collectors with generated ok/failed sequences; assert LLM and collector call counts, the returned content, and that the last failed output appears in `ValidationFailedError` and in the retry messages
    - **Property 17: Collection failures feed the retry loop**
    - **Validates: Requirements 3.7, 3.8, 3.12, 3.13, 9.8**

- [x] 16. Add the GitHub Actions workflow
  - [x] 16.1 Create `.github/workflows/ci.yml`
    - Triggers `push` and `pull_request`; `permissions: contents: read`; one job on `ubuntu-latest` with Python 3.12 and pip cache; steps: checkout, setup-python, `pip install -r requirements.txt`, `python -m pytest`
    - Job-level `env: FORBIDDEN_NAMES: ${{ secrets.FORBIDDEN_NAMES }}`; final step with `if: ${{ env.FORBIDDEN_NAMES != '' }}` that writes the value to `$RUNNER_TEMP/forbidden_names.txt` and runs `python scripts/check_forbidden_names.py` with `FORBIDDEN_NAMES_FILE` pointing to it
    - No `AZURE_OPENAI_*` variable anywhere in the file
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8_

  - [x]* 16.2 Add a layout test for the workflow
    - File: `tests/test_repo_layout.py`
    - Plain-text checks (no YAML dependency): file exists, contains `python -m pytest`, `pip install -r requirements.txt`, `contents: read`, the guarded forbidden names step, and no `AZURE_OPENAI`
    - _Requirements: 10.1, 10.3, 10.4, 10.6, 10.7, 10.8_

- [x] 17. Update the README
  - [x] 17.1 Document the new behavior in `README.md` (pt-BR)
    - In the usage section: abbreviated options such as `--forc` are rejected with exit code 2
    - In the features or architecture section: generated tests must import the target module and pass `pytest --collect-only` (30 s limit, subprocess, executes the top-level code of the module and of the generated file, so review before use)
    - In the tests section: mention the CI workflow, and that the forbidden names step needs the `FORBIDDEN_NAMES` secret
    - Keep the 12 required headings, the pt-BR rule and the no-course-name rule
    - _Requirements: 7.1, 7.2, 8.8, 3.12, 10.6_

- [x] 18. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Property tests use Hypothesis with `max_examples` of at least 100 (200 for fence and validator properties)
- All tests run offline with no Azure variables set; the real Azure generation of the example tests is a manual step done by the owner
- Tasks 13 to 18 were added in a later spec update; the status of tasks 1 to 12 is unchanged
- The first run of the CI workflow on GitHub (Requirements 10.2, 10.5) is a manual check after the push
- The `pip install` check (Requirement 8.2) and the course-name scan (Requirements 7.8, 7.9) are manual or pre-commit steps outside the pytest suite

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["2.1", "3.1", "4.1", "5.1", "5.3", "7.1", "10.1", "11.2"] },
    { "id": 2, "tasks": ["2.2", "2.5", "3.2", "3.4", "4.2", "4.3", "4.4", "4.5", "4.6", "5.2", "5.4", "6.1", "10.2"] },
    { "id": 3, "tasks": ["6.2", "6.3", "7.2", "7.3", "7.4", "9.1"] },
    { "id": 4, "tasks": ["2.3", "2.4", "3.3", "9.2", "9.3", "9.4", "11.1"] },
    { "id": 5, "tasks": ["11.3"] },
    { "id": 6, "tasks": ["13.1", "14.1", "15.1", "15.3", "16.1"] },
    { "id": 7, "tasks": ["13.2", "14.2", "15.2", "15.4", "15.5", "15.6"] },
    { "id": 8, "tasks": ["13.3", "15.7", "16.2", "17.1"] }
  ]
}
```
