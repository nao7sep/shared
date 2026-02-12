playing with ais to generate content that we want often takes more time (with my limited prompting skills). so, here are my quick notes.

## 2026-02-12

main method wont be wrapped in try/except. one day, i might. for now, as a python newbie with less than 2 weeks of experience, i would like to see what happens if i dont. in general, i am intentionally avoiding except-all blocks for the same reason.

unix style paths may be emitted to log files on windows as well. that is ok. not very pretty, but harmless.

we probably can extract redirect destination urls from vertex ai's citation urls' seemingly base64 parts and we probably dont need to actually hit the servers just to get the redirection responses, but this may change; they may switch to short urls any time. the citation urls' responsibility is to give the destination urls when accessed. so, app accesses them.

app doesnt download and cache all cited pages or extract <title>s from them or display/log thoughts or have a debug option to log all request/response bodies. i thought about these and implemented some, but that was over-engineering. sometimes, not doing what we think we can is harder than doing it. :)

if you want full control over all requests/responses, use cli tools such as github copilot cli, claude code, codex cli, gemini cli and parse their json/jsonl files.

poly-chat's advantages are: designed-to-be-git-friendly minimal chat history files, reasonable logs, switchable 7 ais, switchable system prompts, retry/secret modes, rewind command, title/summary generation, safety checks and compose mode where enter key doesnt accidentally send the message (which is extremely helpful for ime users). and it does search and stores citations.

the only feature i havent implemented is "smart context". when we interact with an ai to learn, we usually ask short questions and ais return long responses. do we need to send ALL ai responses each time? no, not really.

i am one of those who think ais are all about what data to give and how to give it. so, "this short prompt gets me everything" people - they are just not tackling real hard issues. context is key. probably, it always will be. when we have discussed things with ais, what's valuable is not the ais' responses, but what WE have said. that is what i strongly believe. that is the very biggest reason why i wrote poly-chat. if you use it, you'll notice that the app is all about context persistence.

smart context, when implemented, will send just enough of summarized-and-persistent ai responses for the current ai to know how all pairs of user message #n and #n+1 connect conceptually. theoretically, this should support years of communication with 1000+ turns at affordable cost. it should be suitable for business strategy, physical training, parenting, etc.

i havent implemented this very important feature because, with cache hits and careful context management (where you utilize retry/secret modes to add only what's truly valuable to the chat history), communication can probably go on for quite some time, already. also, if we use a system prompt that asks the ai to speak very little (like only vitally important questions to the user), we can defer the need to summarize ai responses. and, before i change my mind and implement it, there's a good chance that ais will have infinite context sizes for low prices. so, currently, no rush.
