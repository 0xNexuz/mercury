FROM ghcr.io/foundry-rs/foundry:latest
WORKDIR /contracts
COPY . .
RUN forge install foundry-rs/forge-std --no-git
CMD ["forge", "test", "-vv"]

