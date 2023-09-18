# Contributing to Arkime AWS All In One

:sparkles: Glad to see you here! :sparkles:

---

### Just have a question :question:

* Visit our [FAQs](https://arkime.com/faq)
* Or talk to us directly in the [Arkime Slack](https://slackinvite.arkime.com/)

---

### Where do I start? :traffic_light:

First, checkout the main [Arkime AWS AIO README](README.md) for information on how to build and run Arkime. We do all development on MacBook Pros.

#### How do I contribute?

#### Documentation! :page_with_curl:

Documentation, READMEs, examples, and FAQs are important. Please help improve and add to them.

#### Bugs :bug: :beetle: :ant:

**Before submitting a bug report:**
* Ensure the bug was not already reported by searching for [existing issues in Arkime AWS AIO](https://github.com/arkime/aws-aio/issues)
  * If an issues is already open, make a comment that you are experiencing the same thing and provide any additional details
* Check the [FAQs](https://arkime.com/faq) for a list of common questions and problems

Bugs are tracked as [GitHub Issues](https://guides.github.com/features/issues/).
**Please follow these guidelines when submitting a bug:**
* Provide a clear and descriptive title
* Describe the exact steps to reproduce the problem
* Explain the expected behavior

#### Feature Requests :sparkles:

Feature requests include new features and minor improvements to existing functionality.

Feature requests are tracked as [GitHub Issues](https://guides.github.com/features/issues/).
**Please follow these guidelines when submitting a feature request:**
* Please use a [fork](https://guides.github.com/activities/forking/) to submit a [pull request](https://help.github.com/articles/creating-a-pull-request/) for your contribution.
* Provide a clear and descriptive title
* Describe the suggested feature in as much detail as possible
* Use examples to help us understand the use case of the feature
* If you are requesting a minor improvement, describe the current behavior and why it is not sufficient
* If possible, provide examples of where this feature exists elsewhere in other tools

#### Pull Requests :muscle:

**We welcome all collaboration!** If you can fix it or implement it, please do! :hammer:
To implement something new, please create an issue first so we can discuss it together.

**To better help us review your pull request, please follow these guidelines:**
* Provide a clear and descriptive title
* Clearly describe the problem and solution
* Include the relevant issue number(s) if applicable
* Run unit tests and lint as [described below](how-to-run-the-unit-tests-&-lint)
* When creating a Pull Request please follow [best practices](https://github.com/trein/dev-best-practices/wiki/Git-Commit-Best-Practices) for creating git commits.
* When your code is ready to be submitted, submit a Pull Request to begin the code review process.

#### How to run the unit tests & lint

We require that the ruff linter and unit tests pass before merging PRs.

##### Step 1 - Activate your Python virtual environment

To isolate the Python environment for the project from your local machine, create virtual environment like so:
```
python3 -m venv .venv
source .venv/bin/activate
(cd manage_arkime ; pip install -r requirements.txt)
```

You can exit the Python virtual environment and remove its resources like so:
```
deactivate
rm -rf .venv
```

Learn more about venv [here](https://docs.python.org/3/library/venv.html).

##### Step 2 - Run Pytest
The unit tests are executed by invoking Pytest:

```
python -m pytest test_manage_arkime/
```

You can read more about running unit tests with Pytest [here](https://docs.pytest.org/en/7.2.x/how-to/usage.html).

##### Step 3 - Run Ruff
The Python linter is executed by invoking Ruff:
```
ruff .
```

You can read more about Python linting with Ruff [here](https://beta.ruff.rs/docs/).

##### Step 4 - Run eslint
The Typescript linter is executed by invoking [eslint]((https://eslint.org/):
```
npx eslint .
```
