Dockerfile
-------
**Pre-requisite** Make sure your `docker` runs in `rootless` mode. If you can run 
```
docker run hello-world
```
without `sudo`, you are good to go. 

### Change API Key Before Proceeding

Inside `Dockerfile`, replace the `OPENAI_API_KEY`, with your openAI api key. 

```
ENV OPENAI_API_KEY=sk-proj-XXXX
```

Run the following command to build the docker image
```
docker build --no-cache -t mcp_app .
```

To test

```
docker run -it mcp_app
```

Enjoy chatting!