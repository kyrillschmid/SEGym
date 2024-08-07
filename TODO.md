# TODOs
The project is in a runnable state, generating meaningful data. However, there are still some things that could be improved.
- [ ] Log incorrectly generated patches instead of just fixing them 
- [ ] Make entire docker container generation async to always have a container ready
- [ ] Instead of creating new containers for every patch, create a root container, install the repo and requirements there, and then use `docker commit root root_copy; docker run root_copy` for every patch
- [ ] Integrate into W&B for logging
- [ ] Automatically read `devcontainer.json`, `.github/workflows`, ... to determine test commands and environment
- [ ] Implement all remaining stubs
- [ ] `api.State` should contain a git hash of the directory, allowing to clear observer caches if files are modified
- [ ] Implement a [hybrid retrieval](https://haystack.deepset.ai/tutorials/33_hybrid_retrieval) to combine `InMemoryEmbeddingRetriever` and `InMemoryBM25Retriever`
- [ ] Add `SentenceWindowRetrieval` to `ast`.
- [ ] Add caching to `Store`
- [ ] Add cleanups: `docker container prune` and auto-delete `temp` directory
- [ ] Case study comparing different retrieval methods
- [ ] Check Code Map Retrieval performance with different LLMs
- [ ] Test Code Map Retrieval with different readers (specifically `ast`)