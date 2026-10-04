# No-fallback policy (Thinkube platform default)

A fallback hides the state that needs fixing. The system keeps running on
a substitute, and the fault appears later, far from its cause.

## What is a fallback (do not add)

- A made-up value in place of a required one: a hard-coded default, an
  empty string, a constructed value, an empty result.
- Swallowing an error to keep going: "except: return default", "|| true",
  "ignore_errors".
- Trying a substitute when the real thing fails: another file, another
  endpoint, other credentials.

## What is not a fallback (keep)

- A deliberate order of real sources, where each one is the right answer on
  some install or deploy path. Example: the password from the request, else
  ANSIBLE_BECOME_PASSWORD, else SYSTEM_PASSWORD. Before removing a source,
  find out which path sets it.
- A default that a specification defines. Name the specification.
- A limited retry of the same operation for a failure that can clear on its
  own, ending in an error that says what failed.

## What to do

- When something required is missing, stop with an error that names what is
  missing and how to provide it.
- A fallback in code you are changing: remove it in the same change, and say
  what you removed.
- A fallback anywhere else, or while only answering a question: name it in
  one line and wait.
- Never add a fallback without asking. If one seems necessary, say what it
  would hide, and wait.
- Backward compatibility is a decision, not a habit. Ask before keeping an
  old path alive, and give it a condition for removal.
