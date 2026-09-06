FROM ghcr.io/foundry-rs/foundry:latest
ENTRYPOINT []
WORKDIR /contracts
COPY . .
RUN forge install foundry-rs/forge-std --no-git
CMD ["forge", "test", "-vv"]
