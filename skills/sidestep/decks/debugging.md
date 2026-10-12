# Debugging

- Explain the problem in three sentences to someone who has never seen this codebase.
- Which assumption have you never actually checked? Check it now.
- Pretend the error message is literally and precisely true.
- Find a place where this already works, and compare.
- What changed most recently? Start there.
- Undo your last three changes and approach from a different side.
- Solve the smallest possible version of this problem first.
- Delete half of the code involved. Does the problem survive?
- You've been reading code. Read the logs, data, or network traffic instead.
- Write the failing test before touching anything else.
- What would the most boring solution be?
- Make it work ugly, then make it right.
- Is this the right problem, or a symptom of one level up?
- Who might depend on this broken behavior?
- Write down what you know versus what you only believe.
- Search the issue tracker and history instead of the code.
- Remove something instead of adding something.
- Start a fresh session with only the essentials and see what it notices.
