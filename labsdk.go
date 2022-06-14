package labsdk

// This file is only importing our go dependencies, so they won't be deducted with `go mod tidy`
// The actual code, is being auto-generated via the `setup.py` file, and is not commited to the repo(gitignore'd)
import (
	_ "github.com/natun-ai/natun/pkg/pyexp"
)
