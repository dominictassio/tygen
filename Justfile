build:
  docker build -t tygen .

run:
  docker run -v $(pwd)/results:/usr/src/app/results -it --rm tygen

clean:
  yes | rm -r results/results.csv || true