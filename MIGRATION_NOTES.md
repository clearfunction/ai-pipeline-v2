# AI Pipeline v2 - Migration Notes from v1

## Successfully Extracted from v1

### ✅ Working Credentials
- **GitHub Token**: `ghp_REDACTED` (working)
- **GitHub Username**: `rakeshatcf`
- **Netlify Token**: `nfp_REDACTED` (working)
- **OpenAI & Anthropic API Keys**: Copied from working v1 setup
- **AWS Account**: `008537862626`, Region: `us-east-1`

### ✅ Proven Dependencies
- Replaced `PyPDF2` → `pypdf` (proven working in v1)
- Added `aws-lambda-powertools` (missing in original v2)
- Added `langchain-community`, `sentence-transformers`
- Updated to proven versions from v1 `requirements.txt`

### ✅ Enhanced Error Handling
- Copied `wait_for_lambda_available()` function from v1 deployment script
- Added proper function existence checks with retry logic
- Implemented sequential update process (code → wait → config)
- Added detailed status reporting and error messages

### ✅ Bucket Naming Strategy
- **v2 Pattern**: `ai-pipeline-v2-{type}-{account}-{region}`
- **Differentiated from v1**: `ai-pipeline-{type}-{account}-{region}`
- Maintains proven account/region detection patterns

### ✅ Test Data Evolution
- `working-v1-format.json`: Compatible with v1 lambda invoke patterns
- `end-to-end-test.json`: New multi-document format for v2 story-based approach
- Preserves working GitHub username and metadata patterns

## Key Differences from v1

### 🆚 Architecture Changes
| Aspect | v1 | v2 |
|--------|----|----|
| **Functions** | 5 monolithic lambdas | 10 focused lambdas |
| **Deployment** | Docker + ECR containers | Zip-only deployment |
| **Generation** | All-at-once | Story-based incremental |
| **Review** | Post-generation | Built-in PR workflow |
| **Documents** | Single input | Multi-format intake |

### 🆚 Bucket Strategy
| Type | v1 | v2 |
|------|----|----|
| **Raw** | `ai-pipeline-raw-*` | `ai-pipeline-v2-raw-*` |
| **Processed** | `ai-pipeline-processed-*` | `ai-pipeline-v2-processed-*` |
| **New** | N/A | `ai-pipeline-v2-vectors-*` |

### 🆚 Function Naming
| Type | v1 | v2 |
|------|----|----|
| **Pattern** | `code-scaffolding` | `ai-pipeline-v2-document-processor-dev` |
| **Arguments** | `./deploy.sh code_scaffolding` | `./deploy-single.sh document-processor` |
| **No Conversion** | Underscores → hyphens | Direct lambda name match |

## Ready for Independent Repository

### ✅ Complete Separation
- **No Dependencies**: v2 creates all new AWS resources
- **No Conflicts**: Different naming patterns prevent collision
- **Independent Testing**: Separate test data and invoke patterns
- **Clean Git History**: Fresh repository with no v1 legacy

### ✅ Proven Foundations
- **Working Credentials**: No re-authentication needed
- **Error Handling**: Battle-tested deployment patterns
- **Dependencies**: Proven library versions
- **AWS Configuration**: Known working account/region setup

### ✅ Enhanced Capabilities
- **10 Focused Lambdas**: Each with single responsibility
- **Story-Based Development**: Incremental generation approach
- **Human Review Integration**: Built-in PR workflows
- **Multi-Document Processing**: PDFs, transcripts, emails, chats
- **Modern Infrastructure**: TypeScript CDK, composable design

## Next Steps for Independent Repository

1. **Move ai-pipeline-v2**: Copy entire directory to new repository location
2. **Initialize Git**: Fresh git repository with clean history
3. **Deploy Infrastructure**: `cd infrastructure && npm run deploy-dev`
4. **Deploy Lambdas**: `./scripts/deploy-all.sh dev`
5. **Test End-to-End**: `./scripts/test-lambda.sh document-processor dev`

The v2 system is now completely independent and ready for deployment with proven working patterns from v1.