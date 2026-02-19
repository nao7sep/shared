# TODO

- read the claude code book on mcp, parallel development, sub-agents
- write web app that just sends todo mail
- vocabulary development infrastructure for my daughter
- introduce tk, my first python app that nobody else will use :)
- introduce and release polychat
- automate "recordings => transcription => context"
- learn about github pages, automation
- tackle https://www.darioamodei.com/essay/the-adolescence-of-technology
- analyze page structures of https://openwebf.com/en
- tool to generate font rendering sample images
- tool to compose/print/save/organize documents for my daughter
- prompts to skills
- zip/rar archiver that works just like i want it to
- system to save done-on-mac files on windows persistently
- tool to help organize personal videos/photos
- tool to scan/translate/share paper documents
- split-conversation-into-docs.md as skill
- catalogue of tools and work reports
- report on migration, tk, polychat

## History

### 2026-02-19
- ✅ seek tools to read foreign language books => wrote 2 tools for personal use
- ✅ learn: pypi, github actions, what else? => github actions + tags based auto distribution isnt optimal solution for mono repo

### 2026-02-12
- ❌ check all existing tasks to draw a bigger picture. currently work is in bits => vibe management may work better. we finish what we want, when and while we want to
- ✅ check all remaining tasks in paper notebook
- ❌ hello world python gui apps using different packages => not interested. we'll learn what we need, when we need it
- ❌ try mail/sms apis
- ❌ learn different ways to split text into chunks for embedding
- ❌ try deepl/google translation apis
- ❌ try openai/google transcription apis
- ✅ review polychat and update readme.md => first beta done

### 2026-02-09
- ✅ review tk and update readme.md
- ✅ tk: shouldnt be able to set note to pending task

### 2026-02-08
- ✅ multi-ai cli chat tool => first version of polychat runs. refactored and tested
- ✅ try developing 2 projects in parallel => polychat and tk. it worked

### 2026-02-06
- ✅ refine vibe coding workflow => watched some videos and simplified things

### 2026-02-05
- ❌ add prefix _ to what.md and how.md => did and reverted. made internal_docs instead
- ✅ try using mac keychain => wrote code and tests
- ✅ mechanism to store/retrieve api keys => implemented in polychat
- ❌ docs on config-related python packages => yagni
- ❌ tk: smoother workflow. must be something my windows user wife could use => workflow is just fine
- ❌ tk: task addition without "add"? => risky

### 2026-02-02
- ❌ branch management best practices => my knowledge is enough for now
- ✅ discuss task management cost and its potential relevance to inability to complete trivial tasks (such as pushups) => done. i will think of something
- ❌ tool to compress/extract entire code directory, while gitignoring things => branches work better/faster
- ✅ tk: faster way to show recent tasks. "h" currently shows everything => added today, yesterday and recent commands
- ✅ tk: use emojis in history

### 2026-02-01
- ✅ practice writing the what, following 01 doc => wrote what.md and also work_log.md for tk
- ✅ establish straightforward workflow. inbox zero strategy may be key => wrote tk
- ✅ simple todo management cli tool that works well with git and inbox zero strategy => name of app is tk
- ❌ update HOW.md of tk => source is now single source of truth
- ✅ what's python's Protocol? => interface-ish feature without inheritance
- ✅ sqlalchemy? => entity framework-ish orm. also has dapper-ish lower level features

### 2026-01-30
- ✅ commit initial docs by claude AND the conv log => just the docs
- ✅ beyond compare on macbook as well
- ✅ minimal .gitignore in 2 repos
- ✅ consider replacing _private in docs with secrets => replaced and refactored
- ✅ clone repos on mac mini
- ✅ generate doc on python dependency management
- ✅ what is .zprofile? check it on all pcs => unsuitable for setting api keys as environment variables. plaintext. exposed to all processes. use keychain
- ✅ system-wide python3 is used and poetry isnt found on macbook => fixed
- ✅ make sure poetry is installed via homebrew on all pcs
- ✅ .command files to update homebrew/pip packages AND ones that run ai clis => first half done. second half violates yagni
- ✅ license for the repos and apps that they will contain => gpl good enough
- ❌ generate doc on commonly used metadata => saved in secrets repo
- ❌ tool to view conv logs => if good docs are generated/reviewed, conv logs add no value
- ❌ relearn markdown syntax AND make or find cheat sheet => i seem to know just enough
