# Allen Institute for AI (AI2) Documentation Index
**Last Updated:** November 30, 2025  
**Purpose:** Comprehensive resource map for AI2 models, datasets, and research tools  
**Target User:** Sean Rawlings - AI Systems Architect & Legal Tech Innovator  

---

## 🏛️ Organization Overview

### Core Mission & Principles
| Resource | Description | Link |
|----------|-------------|------|
| **About AI2** | Mission, leadership, Seattle non-profit focus | [allenai.org/about](https://allenai.org/about) |
| **Research Principles** | Open, collaborative, inclusive AI development | [allenai.org/research-principles](https://allenai.org/research-principles) |
| **True Openness Philosophy** | Beyond open source - full transparency | [allenai.org/more-than-open](https://allenai.org/more-than-open) |

---

## 📚 Main Documentation Hub

### Developer Resources
| Resource | Description | Link |
|----------|-------------|------|
| **AI2 Documentation Portal** | Central developer guide for models & datasets | [docs.allenai.org](https://docs.allenai.org) |
| **AI2 Playground** | Interactive testing environment | [Playground Link](https://allenai.org/documentation) |

---

## 🤖 Language Models

### OLMo Family (Open Language Models)
| Model | Description | Access Link | Documentation |
|-------|-------------|-------------|---------------|
| **OLMo 2** | Latest fully open language model (7B, 13B) | [HuggingFace](https://huggingface.co/allenai) | [Model Cards & Usage](https://allenai.org/documentation) |
| **OLMo 2 Instruct** | Instruction-tuned variants with Tülu 3 recipes | [HuggingFace](https://huggingface.co/allenai) | [Instruct Guide](https://allenai.org/documentation) |
| **OLMoE** | Mixture of Experts variant (1B-7B) | [HuggingFace](https://huggingface.co/allenai/OLMoE-1B-7B-0125) | [MoE Documentation](https://allenai.org/documentation) |
| **OLMo Legacy** | Previous versions and variants | [HuggingFace Collection](https://huggingface.co/collections/allenai) | [Release Notes](https://docs.allenai.org/release_notes/olmo-release-notes) |

#### Quick Start Code Examples
```python
# OLMo 2 Usage
import transformers
import torch

model_id = "allenai/llama-tulu-3-8b"
pipeline = transformers.pipeline(
    "text-generation",
    model=model_id,
    model_kwargs={"torch_dtype": torch.bfloat16},
    device_map="auto"
)

# OLMoE Usage  
from transformers import OlmoeForCausalLM, AutoTokenizer
model = OlmoeForCausalLM.from_pretrained("allenai/OLMoE-1B-7B-0125")
tokenizer = AutoTokenizer.from_pretrained("allenai/OLMoE-1B-7B-0125")
```

### Tülu 3 (Post-Training Framework)
| Resource | Description | Link |
|----------|-------------|------|
| **Tülu 3 Models Collection** | State-of-the-art open post-training recipes | [HuggingFace Collection](https://huggingface.co/collections/allenai/tulu-3-models-673b8e0dc3512e30e7dc54f5) |
| **Tülu 3 Framework** | Supervised fine-tuning & RLVR techniques | [Research Papers](https://allenai.org/papers) |

### Molmo (Multimodal Models)
| Resource | Description | Link |
|----------|-------------|------|
| **Molmo Family Overview** | Vision-language models with pointing | [molmo.allenai.org](https://molmo.allenai.org) |
| **Molmo Blog** | Technical details and capabilities | [molmo.allenai.org/blog](https://molmo.allenai.org/blog) |
| **Molmo Paper** | Research methodology and results | [molmo.allenai.org/paper.pdf](https://molmo.allenai.org/paper.pdf) |

---

## 📊 Datasets

### Core Training Datasets
| Dataset | Description | Size | Access | License |
|---------|-------------|------|--------|---------|
| **Dolma** | Large-scale English corpus for LLM training | 3T tokens, 4B docs | [HuggingFace](https://huggingface.co/datasets/allenai/dolma) | ODC-BY |
| **Pixmo** | Multimodal dataset for vision-language models | 712K images, 1.3M captions | [HuggingFace](https://huggingface.co/datasets/allenai/pixmo-docs) | ODC-BY |

#### Dolma Subsets
| Subset | Source | Description | Link |
|--------|--------|-------------|------|
| **Dolma Toolkit** | Processing pipeline | High-performance data curation tools | [GitHub](https://github.com/allenai/dolma) |
| **Dolma Web Documentation** | Technical specs | Complete dataset documentation | [allenai.github.io/dolma](https://allenai.github.io/dolma) |
| **Dolma Data Sheet** | Methodology | Research transparency document | [Dolma PDF](https://allenai.github.io/dolma/docs/assets/dolma-v0_1-20230819.pdf) |

#### PixMo Components
| Component | Purpose | Content | Link |
|-----------|---------|---------|------|
| **PixMo-Cap** | Pre-training VLMs | 712K images, dense captions | [Dataset Details](https://molmo.allenai.org/blog) |
| **PixMo-AskModelAnything** | Q&A capability | 162K Q&A pairs, 73K images | [Dataset Details](https://molmo.allenai.org/blog) |
| **PixMo-Points** | Pointing behavior | 2.3M question-point pairs | [Dataset Details](https://molmo.allenai.org/blog) |
| **PixMo-Docs** | Document understanding | Charts, tables, diagrams | [HuggingFace](https://huggingface.co/datasets/allenai/pixmo-docs) |

### Additional Research Datasets
| Dataset | Description | Use Case | Link |
|---------|-------------|----------|------|
| **WildChat** | Real user-ChatGPT interactions | 1M conversations, multilingual | [AI2 Open Data](https://allenai.org/open-data) |
| **Natural Instructions** | Task generalization | 1,616 NLP tasks, 76 task types | [AI2 Open Data](https://allenai.org/open-data) |
| **Self-Instruct** | Instruction following | Bootstrapped instructional data | [AI2 Open Data](https://allenai.org/open-data) |
| **S2-Corpus** | Academic papers | English open-access papers | [AI2 Open Data](https://allenai.org/open-data) |

---

## 🔧 Development Tools & Frameworks

### AllenNLP (Research Platform)
| Resource | Description | Link |
|----------|-------------|------|
| **AllenNLP Main Repository** | PyTorch-based NLP research library | [GitHub](https://github.com/allenai/allennlp) |
| **AllenNLP Guide** | Comprehensive tutorial and documentation | [GitHub](https://github.com/allenai/allennlp-guide) |
| **AllenNLP Models** | Pre-built model implementations | [GitHub](https://github.com/allenai/allennlp-models) |
| **Plugin Ecosystem** | Community extensions | [Plugin Documentation](https://github.com/allenai/allennlp) |

#### AllenNLP Quick Start
```bash
# Installation
pip install allennlp

# Test installation
allennlp test-install

# Common commands
allennlp train config.jsonnet -s output_dir
allennlp evaluate model.tar.gz test_data.jsonl
allennlp predict model.tar.gz input.jsonl
```

### Development Templates
| Template | Use Case | Link |
|----------|----------|------|
| **Config-based Template** | Experiment specification via config files | [Template Repo](https://github.com/allenai/allennlp) |
| **Code-based Template** | Python-configured experiments | [Template Repo](https://github.com/allenai/allennlp) |

---

## 🔬 Specialized Models & Applications

### Domain-Specific Applications
| Application | Domain | Description | Link |
|-------------|--------|-------------|------|
| **OlmoEarth** | Earth/Climate Science | Foundation models for planetary intelligence | [allenai.org/olmoearth](https://allenai.org/olmoearth) |
| **Skylight** | Ocean Intelligence | Maritime enforcement, IUU fishing detection | [Skylight Platform](https://allenai.org/olmoearth) |
| **olmOCR 2** | Document Processing | State-of-the-art OCR for digitized documents | [AI2 Blog](https://allenai.org/blog) |
| **OLMoASR** | Speech Recognition | Open ASR models trained from scratch | [AI2 Blog](https://allenai.org/blog) |
| **SamudrACE** | Climate Modeling | Coupled 3D ocean-atmosphere models | [AI2 Blog](https://allenai.org/blog) |

### Research Tools
| Tool | Purpose | Description | Link |
|------|---------|-------------|------|
| **Asta** | Scientific Discovery | Agentic platform for research | [AI2 Blog](https://allenai.org/blog) |
| **DataVoyager** | Data Analysis | Drilling down into scientific datasets | [AI2 Blog](https://allenai.org/blog) |
| **Fluid Benchmarking** | Model Evaluation | Adaptive evaluation for LM capabilities | [AI2 Blog](https://allenai.org/blog) |

---

## 📖 Research Publications & Technical Resources

### Academic Output
| Resource | Description | Link |
|----------|-------------|------|
| **AI2 Papers Collection** | All published research papers | [allenai.org/papers](https://allenai.org/papers) |
| **AI2 Blog** | Technical blog posts and announcements | [allenai.org/blog](https://allenai.org/blog) |
| **Research Principles** | Scientific methodology and ethics | [allenai.org/research-principles](https://allenai.org/research-principles) |

### Key Research Areas
- Large Language Model Development & Transparency
- Multimodal AI (Vision-Language Models)
- Post-Training Techniques (Instruction Following, RLHF)
- Scientific AI Applications
- Climate & Earth Science AI
- Document Understanding & OCR
- Speech Recognition
- AI Safety & Alignment

---

## 🛠️ GitHub Organization & Repositories

### Main GitHub Organization
| Repository Category | Description | Link |
|---------------------|-------------|------|
| **AI2 Main Org** | 534+ repositories | [github.com/allenai](https://github.com/allenai) |
| **Core Libraries** | AllenNLP, research tools | [Core Repos](https://github.com/allenai) |
| **Model Repositories** | OLMo, Molmo, Tülu codebases | [Model Repos](https://github.com/allenai) |
| **Dataset Tools** | Dolma toolkit, preprocessing | [Data Repos](https://github.com/allenai) |

### Key Repositories for Development
| Repository | Purpose | Stars | Link |
|------------|---------|-------|------|
| **dolma** | OLMo pre-training data tools | 1.3k+ | [GitHub](https://github.com/allenai/dolma) |
| **allennlp** | NLP research platform | 11k+ | [GitHub](https://github.com/allenai/allennlp) |
| **ai2thor** | Visual AI platform | 800+ | [GitHub](https://github.com/allenai/ai2thor) |
| **allennlp-guide** | Learning materials | - | [GitHub](https://github.com/allenai/allennlp-guide) |

---

## 🔗 Model Access & Integration

### Hugging Face Collections
| Collection | Models Included | Link |
|------------|-----------------|------|
| **OLMo Suite** | All OLMo variants | [HuggingFace](https://huggingface.co/collections/allenai) |
| **Tülu 3 Models** | Post-training model family | [HuggingFace](https://huggingface.co/collections/allenai/tulu-3-models-673b8e0dc3512e30e7dc54f5) |
| **Molmo Collection** | Multimodal models | [HuggingFace](https://huggingface.co/collections/allenai) |

### API Integration Examples
```python
# Loading AI2 models via Transformers
from transformers import AutoModelForCausalLM, AutoTokenizer

# OLMo 2 usage
model = AutoModelForCausalLM.from_pretrained("allenai/OLMo-2-7B")
tokenizer = AutoTokenizer.from_pretrained("allenai/OLMo-2-7B")

# Molmo usage  
model = AutoModelForCausalLM.from_pretrained("allenai/Molmo-7B")
tokenizer = AutoTokenizer.from_pretrained("allenai/Molmo-7B")
```

---

## 🧪 Interactive Resources

### Testing Platforms
| Platform | Purpose | Access |
|----------|---------|--------|
| **AI2 Playground** | Interactive model testing | [AI2 Documentation](https://allenai.org/documentation) |
| **Local Development** | Setup guides for models | [Documentation](https://docs.allenai.org) |

### Code Examples & Tutorials
| Resource | Content | Link |
|----------|---------|------|
| **Model Usage Examples** | Quick start code snippets | [docs.allenai.org](https://docs.allenai.org) |
| **AllenNLP Tutorials** | Research framework guides | [AllenNLP Guide](https://github.com/allenai/allennlp-guide) |

---

## 🌍 Applications & Use Cases

### Real-World Deployments
| Application | Domain | Impact | Link |
|-------------|--------|--------|------|
| **Global Mangrove Watch** | Environmental monitoring | 97% accuracy, 10x data efficiency | [OlmoEarth](https://allenai.org/olmoearth) |
| **Maritime Enforcement** | Ocean conservation | IUU fishing detection | [Skylight](https://allenai.org/olmoearth) |
| **Climate Research** | Scientific analysis | Accelerated climate modeling | [AI2 Projects](https://allenai.org) |

### Developer Use Cases
- **Open LLM Development**: Full model pipeline transparency
- **Multimodal Applications**: Vision-language understanding
- **Scientific Computing**: Earth science, climate modeling
- **Document Processing**: OCR, academic paper analysis
- **Research Acceleration**: Tools for scientific discovery

---

## 🔐 Licensing & Usage

### License Framework
| Resource | License | Usage Rights | Restrictions |
|----------|---------|--------------|-------------|
| **Model Weights** | Apache 2.0 / ODC-BY | Commercial use allowed | Attribution required |
| **Datasets** | ODC-BY / Impact License | Research & commercial | Some redistribution limits |
| **Code Repositories** | Apache 2.0 | Open source development | Attribution required |

### Responsible Use Guidelines
| Guideline | Description | Link |
|-----------|-------------|------|
| **AI2 Responsible Use** | Ethical AI development principles | [AI2 Guidelines](https://allenai.org/research-principles) |
| **Dataset Usage Terms** | Proper attribution and usage | [Individual Dataset Pages](https://allenai.org/open-data) |

---

## 📧 Support & Community

### Getting Help
| Resource | Purpose | Contact |
|----------|---------|---------|
| **GitHub Issues** | Technical problems, feature requests | [Repository Issues](https://github.com/allenai) |
| **OlmoEarth Support** | Platform-specific help | olmoearth@allenai.org |
| **General Inquiries** | Research collaboration, partnerships | [allenai.org/about](https://allenai.org/about) |

### Community Engagement
| Platform | Description | Link |
|----------|-------------|------|
| **Research Papers** | Academic publications | [allenai.org/papers](https://allenai.org/papers) |
| **Blog Posts** | Technical insights and updates | [allenai.org/blog](https://allenai.org/blog) |
| **Open Source Contributions** | Community contributions welcome | [GitHub](https://github.com/allenai) |

---

## 🔄 Sean's Project Integration Points

### Juniper Memory System Relevance
- **Open Datasets**: Dolma toolkit for large-scale data processing
- **Model Integration**: Local deployment of OLMo models
- **Document Processing**: olmOCR 2 for legal document analysis
- **Embedding Generation**: Open models for vector creation

### Legal Tech Applications
- **Document Understanding**: Molmo for legal document analysis
- **OCR Capabilities**: olmOCR 2 for digitized legal documents  
- **Knowledge Extraction**: Scientific paper processing techniques
- **Multi-modal Analysis**: Vision-language models for complex documents

### Development Frameworks
- **AllenNLP**: Research-grade NLP pipeline development
- **Open Model Training**: Full transparency pipeline
- **Large-scale Processing**: Dolma toolkit patterns

---

## 🔄 Update Schedule & Maintenance

### Monitoring Strategy
- **Quarterly Reviews**: Check for new model releases
- **Monthly Blog Monitoring**: Track technical announcements
- **Repository Watching**: Key GitHub repositories for updates
- **Paper Publication Tracking**: New research developments

### Critical Resources for Bookmarking
1. **Main Documentation**: [docs.allenai.org](https://docs.allenai.org)
2. **Model Collections**: [HuggingFace AI2](https://huggingface.co/allenai)
3. **GitHub Organization**: [github.com/allenai](https://github.com/allenai)
4. **Technical Blog**: [allenai.org/blog](https://allenai.org/blog)
5. **Dataset Portal**: [allenai.org/open-data](https://allenai.org/open-data)

---

**Index Maintenance Notes:**
- Update model versions quarterly
- Track new dataset releases  
- Monitor licensing changes
- Add new research applications
- Review community tool developments

**Last Comprehensive Update:** November 30, 2025  
**Next Review Target:** February 2026
