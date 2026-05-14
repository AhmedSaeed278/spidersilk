.PHONY: help install lint test app-run docker-build helm-lint helm-template kubeconform tf-fmt tf-validate ansible-lint kind-up kind-down kind-deploy clean

REGISTRY ?= docker.io/ahmedsaeed
IMAGE    ?= $(REGISTRY)/spidersilk-csv-app
TAG      ?= 0.1.0
NS       ?= spidersilk

help:
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-22s %s\n", $$1, $$2}'

install: ## Install Python dev deps
	cd app && pip install -e ".[dev]"

lint: ## Ruff + helm lint + terraform fmt + ansible-lint
	cd app && ruff check .
	helm lint helm/spidersilk
	cd infra/terraform && terraform fmt -check -recursive
	cd ansible && ansible-lint .

test: ## Run pytest
	cd app && pytest -q

app-run: ## Run the app locally with autoreload
	cd app && SPIDERSILK_PUBLIC_DIR=/tmp/spidersilk-public uvicorn spidersilk.main:app --reload

docker-build: ## Build container image
	docker build -t $(IMAGE):$(TAG) app

helm-lint: ## helm lint
	helm lint helm/spidersilk

helm-template: ## Render manifests
	helm template spidersilk helm/spidersilk -n $(NS)

kubeconform: ## Validate rendered manifests against k8s schemas
	helm template spidersilk helm/spidersilk -n $(NS) | kubeconform -strict -summary -

tf-fmt: ## Terraform fmt
	cd infra/terraform && terraform fmt -recursive

tf-validate: ## terraform init + validate (no backend)
	cd infra/terraform && terraform init -backend=false && terraform validate

ansible-lint: ## ansible-lint
	cd ansible && ansible-lint .

kind-up: ## Create a local kind cluster
	kind create cluster --name spidersilk

kind-down: ## Delete the local kind cluster
	kind delete cluster --name spidersilk

kind-deploy: ## Build, load, and helm-install into kind
	docker build -t $(IMAGE):$(TAG) app
	kind load docker-image $(IMAGE):$(TAG) --name spidersilk
	kubectl create namespace $(NS) --dry-run=client -o yaml | kubectl apply -f -
	helm upgrade --install spidersilk helm/spidersilk -n $(NS) \
		--set image.repository=$(IMAGE) --set image.tag=$(TAG) \
		--set serviceAccount.annotations="{}" \
		--wait

clean: ## Remove caches
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	rm -rf app/.pytest_cache app/build app/dist app/*.egg-info
