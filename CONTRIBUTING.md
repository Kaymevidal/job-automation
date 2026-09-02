# Contributing to Job Automation Pro

Thanks for considering a contribution. This is a small personal-tool-turned-
open-source project, so the process is intentionally lightweight.

## Getting set up

```
pip install -r requirements.txt
python test_imports.py
python -m src.gui_main
```

You'll also want [Ollama](https://ollama.com) running locally with a model
pulled (`ollama pull gemma2:9b`) to exercise the scoring/resume-tailoring
code paths. The Docker worker (`docker compose up -d`) is optional and not
needed for GUI development.

## Project scope - please read before adding a feature

This app finds and ranks job postings for a candidate. It deliberately does
**not** contact companies, discover or store anyone's personal contact
information, or send anything on the user's behalf - an earlier version did
this (found company emails, drafted Outlook messages) and it was removed
because scraping and storing real people's personal emails for unsolicited
outreach is personal-data processing with no clear legal basis under LGPD
(and similar laws elsewhere). PRs that reintroduce this kind of automation
will not be merged; if you want to discuss it, open an issue first.

## Before submitting a PR

- **Test against the real thing.** If you touch a scraper, run it against
  the live site and check the parsed output, not just that it doesn't
  raise. Selectors and API shapes drift; a passing import doesn't mean the
  data is right. The same goes for anything that calls Ollama - run it and
  read the actual output.
- **Keep changes scoped.** Small, focused PRs are much easier to review
  than ones that mix a feature with unrelated refactors.
- **Match the existing style.** No comments unless they explain a
  non-obvious *why* (a workaround, a hidden constraint) - the code itself
  should explain the *what*. No emojis anywhere in code, logs, or the UI.
- **Run `python test_imports.py`** before opening the PR, and manually
  exercise whatever you changed in the GUI if it touches `src/gui/`.

## Reporting bugs / proposing features

Open a GitHub issue. For scraper bugs, include the site, the search term
you used, and (if possible) what the actual page looked like vs. what the
app parsed - sites change their markup often, so a stale selector is the
most common cause.

## License

By contributing, you agree your contributions will be licensed under the
project's [MIT License](LICENSE).
