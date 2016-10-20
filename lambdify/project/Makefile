default: publish

.PHONY: env

clean:
	rm -r build
	rm dist.zip

build:
	docker run --rm -it -v $(shell pwd):/app quay.io/pypa/manylinux1_x86_64 /app/scripts/build.sh

dist.zip: build
	zip -9 dist.zip README.md
	cd src && zip -r9 ../dist.zip * && cd ..
	cd build && zip -r9 ../dist.zip *

publish: dist.zip
	aws s3 cp dist.zip s3://idaho-vrt-chelm/toa.zip --acl public-read
	# https://s3.amazonaws.com/idaho-vrt-chelm/toa.zip
