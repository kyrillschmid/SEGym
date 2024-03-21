
## Python
diff-patch-search src tests --affected-files  primes.py main_test.py --issue issue.md

## Git
git apply --ignore-space-change --ignore-whitespace --verbose patchGPT.patch

## Docker

docker build -t prime_factor_image . 2> output.txt
docker run --name PrimeFactors prime_factor_image
docker cp PrimeFactors:/usr/src/app/test_output.txt ./test_output.txt
