.PHONY: doctor test test-review-agent demo renderer-install studio
doctor:
	python3 -m storyforge doctor
test:
	python3 -m unittest discover -s tests -v
test-review-agent:
	cd agents/youtube-creative-review-agent && node --test
demo:
	python3 -m storyforge demo
renderer-install:
	cd renderer && npm ci
studio:
	cd renderer && npm run studio
