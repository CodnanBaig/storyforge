.PHONY: doctor test demo renderer-install studio
doctor:
	python3 -m storyforge doctor
test:
	python3 -m unittest discover -s tests -v
demo:
	python3 -m storyforge demo
renderer-install:
	cd renderer && npm ci
studio:
	cd renderer && npm run studio
