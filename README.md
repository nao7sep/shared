# shared

## todo

- branch management best practices
- check all existing tasks to draw a bigger picture. currently work is in bits
- tool to compress/extract entire code directory, while gitignoring things
- check all remaining tasks in paper notebook
- discuss task management cost and its potential relevance to inability to complete trivial tasks (such as pushups)
- practice writing the what, following 01 doc
- read the claude code book on mcp, parallel development, sub-agents
- what's python's Protocol?
- try developing 2 projects in parallel
- try using mac keychain
- hello world python gui apps using different packages
- establish straightforward workflow. inbox zero strategy may be key
- simple todo management cli tool that works well with git and inbox zero strategy
- sqlalchemy?
- update HOW.md of tk

### done

- commit initial docs by claude AND the conv log => just the docs
- beyond compare on macbook as well
- minimal .gitignore in 2 repos
- consider replacing _private in docs with "secrets" => replaced and refactored
- clone repos on mac mini
- generate doc on python dependency management
- what is .zprofile? check it on all pcs => unsuitable for setting api keys as environment variables. plaintext. exposed to all processes. use keychain
- system-wide python3 is used and poetry isnt found on macbook => fixed
- make sure poetry is installed via homebrew on all pcs
- .command files to update homebrew/pip packages AND ones that run ai clis => first half done. second half violates yagni
- license for the repos and apps that they will contain => gpl good enough
- generate doc on commonly used metadata => saved in secrets repo

### declined

- tool to save/restore latest claude conversation log => accountability issue. if we edit logs, we corrupt integrity. if we dont, we'll expose a lot of garbage
- tool to view conv logs => if good docs are generated/reviewed, conv logs add no value
- relearn markdown syntax AND make or find cheat sheet => i seem to know just enough

## tips

- notes, conv logs, etc must be concise. we rarely refer to redundant ones
- directory structure is not just classification and must help us recall context 
