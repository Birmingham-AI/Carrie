# will*AI*am 

## What are we trying to do?  
- build a RAG that answers Birmingham AI community questions based on previous meetings  
- tracks what people are asking  

## What do we need to make this happen?  
- embed google slide summaries  
- transcribe and embed livestreams  
- build db of questions asked  

## Steps  

| Step | Status | Notes |
| ---- | ------ | ----- |
| pull text from monthly meetup slides | IN PROGRESS | pulled 9/25, 10/25, and 11/25 general meetup slides |
| embed slide text | COMPLETE | done for above listed slides |
| create basic chat | COMPLETE | cli tool to ask one-off questions |
| implement RAG & actual chat function | NOT STARTED | no history or ongoing chat atm |
| host somewhere | NOT STARTED | need to convert from cli tool to api call? |
| create database/store for storing chat history | NOT STARTED | idea is to give admins insight to what people are asking |
| create user query upload task | NOT STARTED | take user query, summarize and tag, upload to aforementioned db |
| update bundled embeddings with meeting name and input type | NOT STARTED | would give output with flags for the breakouts as well as if it was in a slide or from the speaker |