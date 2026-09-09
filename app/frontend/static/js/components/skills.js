// =============================================================================
// Skills Form Component
// =============================================================================

const SkillsComponent = (() => {
    const CATEGORIES = [
        { id: 'technical', label: 'Technical Skills', canonical: 'Technical Skills' },
        { id: 'framework', label: 'Frameworks & Libraries', canonical: 'Frameworks & Libraries' },
        { id: 'tool', label: 'Tools & Platforms', canonical: 'Tools & Platforms' },
        { id: 'soft', label: 'Soft Skills', canonical: 'Soft Skills' },
    ];

    function matchCategory(skillCat, catId) {
        if (!skillCat) return catId === 'technical';
        const c = String(skillCat).trim().replace(/[:]+$/, '').toLowerCase();
        if (catId === 'technical') {
            return ['technical', 'technical skills', 'skills', 'tech', 'programming', 'languages', 'programming languages', 'coding', 'core competencies', 'technical proficiencies'].includes(c);
        }
        if (catId === 'framework') {
            return ['framework', 'frameworks', 'libraries', 'frameworks & libraries', 'frameworks and libraries', 'frameworks & tools', 'framework & library'].includes(c);
        }
        if (catId === 'tool') {
            return ['tool', 'tools', 'tools & platforms', 'tools and platforms', 'platforms', 'developer tools', 'technologies', 'devops', 'software', 'environment'].includes(c);
        }
        if (catId === 'soft') {
            return ['soft', 'soft skills', 'interpersonal', 'interpersonal skills', 'professional skills', 'management'].includes(c);
        }
        return c === String(catId).trim().toLowerCase();
    }

    function getCanonicalCategory(catIdOrName) {
        if (!catIdOrName) return 'Technical Skills';
        for (const cat of CATEGORIES) {
            if (cat.id === catIdOrName || matchCategory(catIdOrName, cat.id)) {
                return cat.canonical;
            }
        }
        return String(catIdOrName).trim().replace(/[:]+$/, '');
    }

    const PRELOADED_SKILLS = {
        technical: [
            'JavaScript', 'TypeScript', 'Python', 'Java',
            'C', 'C++', 'C#', 'Go',
            'Rust', 'PHP', 'Ruby', 'Swift',
            'Kotlin', 'Dart', 'R', 'MATLAB',
            'Scala', 'Perl', 'Lua', 'Haskell',
            'Elixir', 'Erlang', 'Clojure', 'F#',
            'Groovy', 'Julia', 'Objective-C', 'Visual Basic',
            'VBA', 'Assembly', 'Solidity', 'Move',
            'Apex', 'ABAP', 'COBOL', 'Fortran',
            'Prolog', 'OCaml', 'Crystal', 'Nim',
            'Zig', 'Odin', 'Bash', 'Shell Scripting',
            'PowerShell', 'SQL', 'PL/SQL', 'T-SQL',
            'HTML', 'HTML5', 'CSS', 'CSS3',
            'Sass', 'SCSS', 'Less', 'XML',
            'YAML', 'JSON', 'Markdown', 'LaTeX',
            'Regular Expressions',
            'GraphQL', 'REST APIs', 'SOAP', 'gRPC',
            'WebSockets', 'WebRTC', 'Server-Sent Events', 'OpenAPI',
            'AsyncAPI', 'OAuth 2.0', 'OpenID Connect', 'JWT',
            'SAML', 'LDAP', 'DNS', 'HTTP',
            'HTTP/2', 'HTTP/3', 'HTTPS', 'TCP/IP',
            'UDP', 'SSH', 'FTP', 'SFTP',
            'SMTP', 'IMAP', 'MQTT', 'AMQP',
            'Webhooks',
            'API Design', 'API Development', 'API Integration',
            'API Security', 'API Testing', 'API Documentation',
            'Microservices', 'Monolithic Architecture',
            'Service-Oriented Architecture', 'Event-Driven Architecture',
            'Serverless Architecture', 'Distributed Systems',
            'Client-Server Architecture', 'Clean Architecture',
            'Hexagonal Architecture', 'Domain-Driven Design',
            'CQRS', 'Event Sourcing', 'Design Patterns',
            'SOLID Principles',
            'Object-Oriented Programming', 'Functional Programming',
            'Procedural Programming', 'Reactive Programming',
            'Concurrent Programming', 'Parallel Programming',
            'Asynchronous Programming', 'Multithreading',
            'Multiprocessing', 'Memory Management',
            'Garbage Collection',
            'Data Structures', 'Algorithms', 'Algorithm Design',
            'Computational Complexity', 'Big O Analysis',
            'Dynamic Programming', 'Recursion', 'Graph Algorithms',
            'Search Algorithms', 'Sorting Algorithms',
            'Greedy Algorithms', 'Backtracking',
            'Operating Systems', 'Computer Architecture',
            'Computer Networks', 'Computer Organization',
            'Compilers', 'Interpreters', 'Distributed Computing',
            'High-Performance Computing', 'Edge Computing',
            'Cloud Computing', 'Fog Computing',
            'Virtualization', 'Containerization',
            'Infrastructure as Code', 'Configuration Management',
            'Site Reliability Engineering', 'Platform Engineering',
            'DevOps', 'DevSecOps', 'GitOps', 'CI/CD',
            'Continuous Integration', 'Continuous Delivery',
            'Continuous Deployment', 'Release Engineering',
            'Build Engineering',
            'Observability', 'Monitoring', 'Logging', 'Tracing',
            'Performance Engineering', 'Performance Optimization',
            'Load Testing', 'Stress Testing', 'Scalability',
            'High Availability', 'Fault Tolerance',
            'Disaster Recovery', 'Backup and Recovery',
            'Capacity Planning', 'Caching', 'Load Balancing',
            'Message Queues', 'Pub/Sub', 'Rate Limiting',
            'Reverse Proxy', 'Service Mesh', 'API Gateway',
            'CDN', 'Autoscaling',
            'Database Design', 'Database Administration',
            'Database Optimization', 'Database Migration',
            'Data Modeling', 'Relational Databases',
            'NoSQL Databases', 'Document Databases',
            'Key-Value Databases', 'Graph Databases',
            'Time-Series Databases', 'Vector Databases',
            'In-Memory Databases',
            'Data Warehousing', 'Data Lakes', 'Data Lakehouse',
            'ETL', 'ELT', 'Data Pipelines',
            'Data Integration', 'Data Governance', 'Data Quality',
            'Data Cataloging', 'Data Lineage',
            'Master Data Management', 'Data Engineering',
            'Big Data', 'Stream Processing', 'Batch Processing',
            'Data Analysis', 'Data Analytics',
            'Business Intelligence', 'Data Visualization',
            'Statistical Analysis', 'Probability', 'Statistics',
            'Linear Algebra', 'Calculus', 'Discrete Mathematics',
            'Optimization', 'Operations Research',
            'A/B Testing', 'Experiment Design',
            'Machine Learning', 'Deep Learning',
            'Supervised Learning', 'Unsupervised Learning',
            'Semi-Supervised Learning', 'Reinforcement Learning',
            'Transfer Learning', 'Federated Learning',
            'Few-Shot Learning', 'Zero-Shot Learning',
            'Self-Supervised Learning', 'Representation Learning',
            'Feature Engineering', 'Feature Selection',
            'Model Training', 'Model Evaluation',
            'Model Deployment', 'Model Monitoring',
            'MLOps', 'LLMOps',
            'Natural Language Processing', 'Computer Vision',
            'Speech Recognition', 'Speech Synthesis',
            'Audio Processing', 'Signal Processing',
            'Image Processing', 'Video Processing',
            'Optical Character Recognition',
            'Information Retrieval', 'Search Systems',
            'Recommendation Systems', 'Anomaly Detection',
            'Forecasting', 'Time-Series Analysis',
            'Clustering', 'Classification', 'Regression',
            'Dimensionality Reduction',
            'Generative AI', 'Large Language Models',
            'Small Language Models', 'Transformers',
            'Prompt Engineering', 'Prompt Design',
            'Prompt Evaluation', 'Prompt Optimization',
            'Retrieval-Augmented Generation', 'RAG',
            'AI Agents', 'Agentic AI', 'Multi-Agent Systems',
            'Tool Calling', 'Function Calling',
            'Structured Outputs', 'Embeddings',
            'Vector Search', 'Semantic Search', 'Hybrid Search',
            'Knowledge Graphs', 'Knowledge Representation',
            'Fine-Tuning', 'LoRA', 'QLoRA',
            'Model Quantization', 'Model Distillation',
            'Model Pruning', 'RLHF', 'RLAIF',
            'AI Evaluation', 'AI Safety', 'Responsible AI',
            'Explainable AI', 'Synthetic Data', 'Multimodal AI',
            'Vision-Language Models', 'Graph Neural Networks',
            'Convolutional Neural Networks',
            'Recurrent Neural Networks', 'GANs',
            'Diffusion Models', 'Neural Networks',
            'Bayesian Modeling', 'AutoML',
            'Hyperparameter Tuning',
            'PostgreSQL', 'MySQL', 'MariaDB', 'SQLite',
            'Microsoft SQL Server', 'Oracle Database',
            'MongoDB', 'Redis', 'Valkey', 'Elasticsearch',
            'OpenSearch', 'Cassandra', 'DynamoDB',
            'Firestore', 'Firebase Realtime Database',
            'CouchDB', 'Couchbase', 'Neo4j', 'ArangoDB',
            'InfluxDB', 'TimescaleDB', 'ClickHouse',
            'Snowflake', 'BigQuery', 'Redshift', 'Databricks',
            'Apache Hive', 'Apache HBase', 'DuckDB',
            'Supabase', 'Neon', 'PlanetScale', 'CockroachDB',
            'TiDB', 'Fauna', 'SurrealDB', 'RethinkDB',
            'RocksDB', 'LevelDB', 'Pinecone', 'Weaviate',
            'Milvus', 'Qdrant', 'Chroma', 'pgvector',
            'Spanner', 'Teradata', 'IBM Db2', 'SAP HANA',
            'Firebird',
            'AWS', 'Microsoft Azure', 'Google Cloud',
            'Oracle Cloud', 'IBM Cloud', 'Cloudflare',
            'DigitalOcean', 'Linode', 'Vultr', 'Heroku',
            'Vercel', 'Netlify', 'Render', 'Fly.io',
            'Railway', 'OpenStack',
            'Amazon EC2', 'Amazon S3', 'AWS Lambda',
            'Amazon RDS', 'Amazon DynamoDB', 'Amazon ECS',
            'Amazon EKS', 'Amazon SQS', 'Amazon SNS',
            'Amazon CloudFront', 'Amazon API Gateway',
            'AWS IAM', 'AWS CloudFormation', 'AWS CDK',
            'Amazon Bedrock',
            'Azure Functions', 'Azure App Service',
            'Azure Kubernetes Service', 'Azure DevOps',
            'Azure SQL', 'Azure Cosmos DB',
            'Azure Blob Storage', 'Azure AI Foundry',
            'Google Compute Engine', 'Google Kubernetes Engine',
            'Cloud Run', 'Cloud Functions', 'Cloud Storage',
            'Cloud SQL', 'Vertex AI', 'Firebase',
            'Cybersecurity', 'Application Security',
            'Network Security', 'Cloud Security',
            'Information Security', 'Endpoint Security',
            'Web Security', 'Mobile Security',
            'Identity and Access Management', 'IAM',
            'Zero Trust', 'Threat Modeling',
            'Threat Intelligence', 'Vulnerability Assessment',
            'Vulnerability Management', 'Penetration Testing',
            'Ethical Hacking', 'Security Auditing',
            'Security Testing', 'Secure Coding',
            'Security Architecture', 'Incident Response',
            'Digital Forensics', 'Malware Analysis',
            'Reverse Engineering', 'Cryptography',
            'Encryption', 'Public Key Infrastructure', 'PKI',
            'Authentication', 'Authorization', 'Access Control',
            'Secrets Management', 'Security Operations',
            'SOC Operations', 'SIEM', 'SOAR',
            'Data Loss Prevention', 'DLP',
            'Governance Risk and Compliance', 'GRC',
            'Risk Assessment', 'Security Compliance',
            'OWASP Top 10', 'OWASP ASVS', 'PCI DSS',
            'ISO 27001', 'SOC 2', 'GDPR',
            'NIST Cybersecurity Framework',
            'Mobile App Development', 'Android Development',
            'iOS Development', 'Cross-Platform Development',
            'Responsive Design', 'Progressive Web Apps', 'PWA',
            'Web Accessibility', 'WCAG',
            'Internationalization', 'Localization',
            'Frontend Development', 'Backend Development',
            'Full-Stack Development',
            'Desktop Application Development',
            'Game Development', 'Embedded Systems',
            'Firmware Development', 'IoT', 'Robotics',
            'AR Development', 'VR Development',
            'XR Development', 'Blockchain Development',
            'Smart Contracts', 'Web3',
            'Distributed Ledger Technology',
            'Unit Testing', 'Integration Testing',
            'End-to-End Testing', 'Regression Testing',
            'Smoke Testing', 'Sanity Testing',
            'Acceptance Testing', 'System Testing',
            'Functional Testing', 'Non-Functional Testing',
            'Exploratory Testing', 'Manual Testing',
            'Automation Testing', 'Test-Driven Development',
            'Behavior-Driven Development', 'Contract Testing',
            'Mutation Testing', 'Snapshot Testing',
            'Cross-Browser Testing', 'Accessibility Testing',
            'Usability Testing', 'QA Engineering',
            'Test Planning', 'Test Case Design',
            'Bug Reporting', 'Defect Tracking',
            'Version Control', 'Source Control',
            'Branching Strategies', 'GitFlow',
            'Trunk-Based Development', 'Code Review',
            'Pair Programming',
            'Technical Documentation', 'Software Documentation',
            'Technical Writing', 'Requirements Analysis',
            'Requirements Engineering', 'Systems Analysis',
            'Software Architecture', 'Solution Architecture',
            'Enterprise Architecture', 'Systems Design',
            'Low-Level Design', 'High-Level Design',
            'UML', 'BPMN', 'ER Modeling', 'Schema Design',
            'Agile', 'Scrum', 'Kanban',
            'Lean Software Development', 'Extreme Programming',
            'SDLC', 'Product Development', 'Product Management',
            'Technical Product Management', 'Project Management',
            'Program Management', 'IT Service Management',
            'ITIL', 'Change Management', 'Incident Management',
            'Problem Management', 'Release Management',
            'Service Management',
            'Linux', 'Unix', 'Windows', 'Windows Server',
            'macOS', 'Android', 'iOS', 'ChromeOS', 'FreeBSD',
            'System Administration', 'Linux Administration',
            'Windows Administration', 'Network Administration',
            'Cloud Administration', 'Server Administration',
            'Active Directory', 'Group Policy',
            'Virtual Machines', 'Storage Management',
            'File Systems', 'Automation', 'Scripting',
            'CLI', 'Command Line',
            'Computer Hardware', 'PC Troubleshooting',
            'Hardware Troubleshooting', 'Network Troubleshooting',
            'Software Troubleshooting', 'Technical Support',
            'Help Desk', 'IT Support', 'Remote Support',
            'System Integration', 'Enterprise Integration',
            'ERP', 'CRM', 'E-commerce', 'Payment Systems',
            'FinTech', 'HealthTech', 'EdTech', 'GovTech',
            'SaaS', 'Multi-Tenancy',
            'Mojo', 'Gleam', 'GDScript', 'Elm', 'PureScript',
            'ReScript', 'Ballerina', 'Q#', 'V', 'Chapel',
            'WebGPU', 'Module Federation', 'Micro-frontends',
            'Context Engineering', 'eBPF', 'Data Mesh',
            'Data Contracts', 'Reverse ETL', 'AI Agent Memory',
            'LLM Evaluation', 'Agent Evaluation', 'RAG Evaluation',
            'AI Observability', 'AI Red Teaming', 'Prompt Injection Defense',
            'DPO', 'Graph RAG', 'Multimodal RAG', 'Mixture of Experts'
        ],

        framework: [
            'React', 'Next.js', 'Vue.js', 'Nuxt',
            'Angular', 'Svelte', 'SvelteKit', 'SolidJS',
            'Qwik', 'Astro', 'Remix', 'Ember.js',
            'Backbone.js', 'Preact', 'Lit', 'Alpine.js',
            'HTMX', 'Stimulus', 'Mithril', 'jQuery',
            'Node.js', 'Express.js', 'Fastify', 'NestJS',
            'Koa', 'Hapi', 'AdonisJS', 'FeathersJS',
            'Meteor', 'Bun', 'Deno',
            'Django', 'Flask', 'FastAPI', 'Starlette',
            'Tornado', 'Bottle', 'Pyramid', 'Sanic',
            'Falcon', 'CherryPy',
            'Spring', 'Spring Boot', 'Spring MVC',
            'Spring Security', 'Hibernate', 'Quarkus',
            'Micronaut', 'Jakarta EE', 'Vert.x',
            'Play Framework',
            'ASP.NET', 'ASP.NET Core', '.NET', '.NET Core',
            'Entity Framework', 'Entity Framework Core',
            'Blazor', 'MAUI',
            'Laravel', 'Symfony', 'CodeIgniter',
            'CakePHP', 'Yii', 'Slim', 'Laminas',
            'Ruby on Rails', 'Sinatra', 'Hanami',
            'Phoenix', 'Plug', 'Ecto',
            'Gin', 'Echo', 'Fiber', 'Chi',
            'Beego', 'Revel',
            'Actix Web', 'Axum', 'Rocket', 'Warp',
            'Tauri',
            'React Native', 'Expo', 'Flutter', 'SwiftUI',
            'UIKit', 'Jetpack Compose', 'Android Jetpack',
            'Xamarin', 'Ionic', 'Capacitor', 'Cordova',
            'Electron', 'Qt', 'GTK', 'Tkinter',
            'PyQt', 'Kivy', 'Avalonia', 'WPF', 'WinUI',
            'Tailwind CSS', 'Bootstrap', 'Material UI', 'MUI',
            'Chakra UI', 'Ant Design', 'Mantine',
            'Semantic UI', 'Bulma', 'Foundation',
            'DaisyUI', 'Shadcn UI', 'Radix UI',
            'Headless UI', 'Styled Components',
            'Emotion', 'CSS Modules',
            'Redux', 'Redux Toolkit', 'Zustand', 'MobX',
            'Recoil', 'Jotai', 'XState', 'Pinia',
            'Vuex', 'NgRx', 'TanStack Query',
            'React Query', 'SWR', 'Apollo Client',
            'Relay', 'RTK Query',
            'GraphQL Apollo', 'Apollo Server',
            'GraphQL Yoga', 'Hasura', 'tRPC',
            'Prisma', 'Drizzle ORM', 'Sequelize',
            'TypeORM', 'Mongoose', 'Knex.js',
            'Objection.js', 'SQLAlchemy', 'Django ORM',
            'Peewee', 'Tortoise ORM', 'Hibernate ORM',
            'Doctrine ORM', 'Active Record',
            'Jest', 'Vitest', 'Mocha', 'Jasmine',
            'Cypress', 'Playwright', 'Selenium',
            'Puppeteer', 'WebdriverIO', 'Testing Library',
            'React Testing Library', 'JUnit', 'TestNG',
            'Pytest', 'Unittest', 'RSpec', 'PHPUnit',
            'NUnit', 'xUnit',
            'Storybook', 'Chromatic',
            'Webpack', 'Vite', 'Rollup', 'Parcel',
            'esbuild', 'SWC', 'Turbopack', 'Babel',
            'Gulp', 'Grunt',
            'TensorFlow', 'PyTorch', 'Keras',
            'Scikit-learn', 'XGBoost', 'LightGBM',
            'CatBoost', 'JAX', 'MXNet',
            'Pandas', 'NumPy', 'SciPy', 'Polars',
            'Dask', 'Modin', 'cuDF', 'Statsmodels',
            'Matplotlib', 'Plotly', 'Bokeh', 'Altair',
            'Dash', 'Streamlit', 'Gradio',
            'OpenCV', 'Pillow', 'Albumentations',
            'Detectron2', 'YOLO', 'Ultralytics',
            'MMDetection',
            'Hugging Face Transformers',
            'Hugging Face Diffusers',
            'Sentence Transformers',
            'spaCy', 'NLTK', 'Gensim',
            'LangChain', 'LangGraph', 'LlamaIndex',
            'Semantic Kernel', 'AutoGen', 'CrewAI',
            'Haystack', 'DSPy', 'PydanticAI',
            'Vercel AI SDK', 'OpenAI Agents SDK',
            'Google ADK', 'Agno', 'Smolagents',
            'ONNX', 'ONNX Runtime', 'TensorRT',
            'OpenVINO', 'MLflow', 'Kubeflow',
            'Ray', 'Ray Serve', 'BentoML',
            'FastText', 'FAISS', 'Annoy',
            'Apache Spark', 'PySpark', 'Apache Flink',
            'Apache Beam', 'Kafka Streams', 'Apache Storm',
            'Airflow', 'Prefect', 'Dagster', 'dbt', 'Luigi',
            'Three.js', 'Babylon.js', 'A-Frame',
            'Phaser', 'PixiJS', 'D3.js', 'Chart.js',
            'Recharts', 'Nivo',
            'Unity', 'Unreal Engine', 'Godot',
            'GameMaker', 'Cocos2d', 'Cocos Creator',
            'ROS', 'ROS 2',
            'OpenZeppelin', 'Hardhat', 'Foundry',
            'Truffle', 'ethers.js', 'web3.js',
            'Serverless Framework', 'AWS SAM', 'AWS CDK',
            'Pulumi', 'Terraform CDK',
            'Socket.IO', 'SignalR', 'RxJS',
            'Project Reactor',
            'React Server Components', 'ElysiaJS',
            'Microsoft AutoGen', 'Mastra', 'LangSmith',
            'Langfuse', 'Arize Phoenix', 'Ragas',
            'DeepEval', 'Promptfoo', 'LiteLLM',
            'Unsloth', 'TensorRT-LLM', 'SGLang'
        ],

        tool: [
            'Git', 'GitHub', 'GitLab', 'Bitbucket',
            'Azure Repos', 'Subversion', 'Mercurial',
            'GitHub Actions', 'GitLab CI/CD', 'Jenkins',
            'CircleCI', 'Travis CI', 'TeamCity',
            'Bamboo', 'Drone CI', 'Buildkite',
            'Argo CD', 'Flux', 'Tekton', 'Spinnaker',
            'Harness',
            'Docker', 'Docker Compose', 'Podman',
            'Kubernetes', 'OpenShift', 'Rancher',
            'Helm', 'Kustomize', 'Istio', 'Linkerd',
            'Consul',
            'Terraform', 'OpenTofu', 'Pulumi',
            'Ansible', 'Chef', 'Puppet', 'SaltStack',
            'Vagrant', 'Packer', 'Nomad',
            'Prometheus', 'Grafana', 'Datadog',
            'New Relic', 'Dynatrace', 'Splunk',
            'Elastic Stack', 'ELK Stack', 'Kibana',
            'Logstash', 'Fluentd', 'Fluent Bit',
            'OpenTelemetry', 'Jaeger', 'Zipkin',
            'Sentry', 'PagerDuty', 'Opsgenie',
            'Postman', 'Insomnia', 'Bruno',
            'Hoppscotch', 'SoapUI', 'Swagger UI',
            'SwaggerHub', 'Stoplight', 'Paw',
            'VS Code', 'Visual Studio', 'IntelliJ IDEA',
            'PyCharm', 'WebStorm', 'Rider', 'CLion',
            'GoLand', 'PhpStorm', 'RubyMine',
            'Android Studio', 'Xcode', 'Eclipse',
            'NetBeans', 'Vim', 'Neovim', 'Emacs',
            'Sublime Text', 'Notepad++', 'Cursor', 'Zed',
            'GitHub Copilot', 'Codex', 'Claude Code',
            'Gemini CLI', 'Continue', 'Cline',
            'Aider', 'Tabnine', 'Codeium', 'Windsurf',
            'Jira', 'Confluence', 'Trello', 'Asana',
            'Monday.com', 'ClickUp', 'Linear', 'Notion',
            'Basecamp', 'Microsoft Project',
            'Slack', 'Microsoft Teams', 'Discord',
            'Zoom', 'Google Meet',
            'Figma', 'FigJam', 'Adobe XD', 'Sketch',
            'Framer', 'Canva', 'Miro', 'Whimsical',
            'Lucidchart', 'draw.io', 'Balsamiq',
            'Adobe Photoshop', 'Adobe Illustrator',
            'Adobe After Effects', 'Adobe Premiere Pro',
            'Blender', 'GIMP', 'Inkscape',
            'NPM', 'Yarn', 'pnpm', 'Bun Package Manager',
            'pip', 'Poetry', 'Pipenv', 'uv', 'Conda',
            'Maven', 'Gradle', 'NuGet', 'Cargo',
            'Composer', 'RubyGems', 'Homebrew',
            'Chocolatey', 'Winget', 'APT', 'Snap',
            'Flatpak',
            'Webpack', 'Vite', 'Rollup', 'Parcel',
            'esbuild', 'Babel', 'SWC', 'Turborepo',
            'Nx', 'Lerna', 'Make', 'CMake', 'Ninja',
            'Bazel',
            'ESLint', 'Prettier', 'Biome', 'Stylelint',
            'SonarQube', 'SonarCloud', 'Semgrep',
            'CodeQL', 'Snyk', 'Dependabot',
            'Renovate', 'Trivy', 'Grype',
            'OWASP ZAP', 'Burp Suite', 'Nmap',
            'Wireshark', 'Metasploit', 'Nessus',
            'OpenVAS', 'Kali Linux',
            'HashiCorp Vault', '1Password',
            'AWS Secrets Manager', 'Azure Key Vault',
            'Google Secret Manager',
            'RedisInsight', 'pgAdmin', 'DBeaver',
            'DataGrip', 'MySQL Workbench',
            'SQL Server Management Studio',
            'Oracle SQL Developer', 'MongoDB Compass',
            'Studio 3T', 'TablePlus', 'HeidiSQL',
            'phpMyAdmin', 'OpenSearch Dashboards',
            'Kafka', 'Apache Kafka', 'RabbitMQ',
            'Apache Pulsar', 'NATS', 'ActiveMQ',
            'Redpanda', 'Amazon SQS', 'Google Pub/Sub',
            'Apache Spark', 'Apache Hadoop',
            'Apache Airflow', 'dbt', 'Databricks',
            'Snowflake', 'BigQuery',
            'Looker', 'Looker Studio', 'Power BI',
            'Tableau', 'Qlik Sense', 'Metabase',
            'Superset', 'Mode Analytics',
            'Jupyter Notebook', 'JupyterLab',
            'Google Colab', 'Kaggle', 'Anaconda',
            'Weights & Biases', 'TensorBoard',
            'Hugging Face', 'Ollama', 'LM Studio',
            'OpenAI API', 'Anthropic API',
            'Google Gemini API', 'Groq', 'Together AI',
            'Replicate', 'OpenRouter',
            'Pinecone', 'Weaviate', 'Qdrant',
            'Milvus', 'Chroma',
            'AWS Management Console', 'AWS CLI',
            'Azure Portal', 'Azure CLI',
            'Google Cloud Console', 'gcloud CLI',
            'Cloudflare Dashboard',
            'Vercel', 'Netlify', 'Render', 'Railway',
            'Fly.io', 'Heroku', 'DigitalOcean',
            'Firebase', 'Supabase', 'Neon',
            'VirtualBox', 'VMware Workstation',
            'VMware vSphere', 'Hyper-V', 'Proxmox',
            'QEMU',
            'Linux', 'Ubuntu', 'Debian', 'Fedora',
            'Red Hat Enterprise Linux', 'CentOS',
            'Rocky Linux', 'AlmaLinux', 'Arch Linux',
            'Windows', 'Windows Server', 'macOS',
            'WSL', 'PowerShell', 'Bash', 'Zsh',
            'PuTTY', 'MobaXterm', 'WinSCP', 'FileZilla',
            'Termius', 'OpenSSH', 'Remote Desktop',
            'AnyDesk', 'TeamViewer',
            'Active Directory', 'Microsoft Entra ID',
            'Okta', 'Auth0', 'Keycloak',
            'Microsoft Intune', 'Jamf',
            'ServiceNow', 'Zendesk', 'Freshservice',
            'Freshdesk',
            'Salesforce', 'HubSpot', 'Odoo',
            'SAP', 'SAP S/4HANA', 'Oracle ERP',
            'Microsoft Dynamics 365',
            'WordPress', 'Drupal', 'Joomla',
            'Shopify', 'WooCommerce', 'Magento',
            'Webflow',
            'Google Analytics', 'Google Tag Manager',
            'Search Console', 'Hotjar', 'Mixpanel',
            'Amplitude', 'PostHog',
            'Stripe', 'PayPal', 'Braintree', 'Adyen',
            'Cloudinary', 'ImageKit', 'Uploadcare',
            'Arduino IDE', 'PlatformIO', 'Raspberry Pi',
            'MATLAB', 'LabVIEW',
            'Fiddler', 'Charles Proxy', 'mitmproxy',
            'ngrok', 'Cloudflare Tunnel', 'LocalTunnel',
            'Docker Desktop', 'Lens', 'k9s', 'Portainer',
            'GitHub Desktop', 'SourceTree',
            'GitKraken', 'Fork',
            'PostgreSQL CLI (psql)', 'MySQL CLI',
            'SQLite CLI', 'Redis CLI', 'MongoDB Shell',
            'OpenAPI Generator', 'GraphQL Playground',
            'GraphiQL', 'Apollo Studio',
            'JMeter', 'k6', 'Gatling',
            'Locust', 'Artillery',
            'Appium', 'BrowserStack', 'Sauce Labs',
            'TestRail', 'Zephyr', 'Xray', 'qTest',
            'Docusaurus', 'MkDocs', 'Sphinx',
            'Read the Docs', 'GitBook',
            'Mermaid', 'PlantUML', 'StarUML',
            'Enterprise Architect',
            'Faker', 'Mockoon', 'WireMock',
            'Mock Service Worker', 'JSON Server',
            'Cilium', 'Envoy', 'Crossplane',
            'Argo Workflows', 'Argo Rollouts',
            'Airbyte', 'Fivetran', 'Meltano', 'Debezium',
            'Apache NiFi', 'Apache Hudi', 'Trino', 'Presto',
            'Dremio', 'Great Expectations', 'OpenMetadata', 'DataHub',
            'SBOM', 'CycloneDX', 'SPDX', 'MITRE ATT&CK',
            'CIS Benchmarks', 'Ghidra', 'YARA', 'Wazuh',
            'Falco', 'Suricata',
            'Model Context Protocol', 'MCP', 'MCP Servers',
            'MCP Clients', 'Agent2Agent Protocol', 'A2A Protocol'
        ],

        soft: [
            'Effective Communication', 'Verbal Communication',
            'Written Communication', 'Active Listening',
            'Presentation Skills', 'Public Speaking',
            'Storytelling', 'Business Communication',
            'Technical Communication',
            'Nonverbal Communication',
            'Interpersonal Skills', 'Relationship Building',
            'Networking', 'Rapport Building', 'Empathy',
            'Emotional Intelligence', 'Self-Awareness',
            'Social Awareness', 'Cultural Awareness',
            'Cross-Cultural Communication',
            'Respectfulness', 'Patience',
            'Teamwork', 'Team Collaboration',
            'Cross-functional Collaboration',
            'Remote Collaboration', 'Virtual Collaboration',
            'Stakeholder Collaboration', 'Cooperation',
            'Team Leadership', 'Leadership',
            'Servant Leadership', 'Situational Leadership',
            'Strategic Leadership', 'People Management',
            'Team Management', 'Delegation', 'Motivation',
            'Coaching', 'Mentoring',
            'Conflict Resolution', 'Conflict Management',
            'Negotiation', 'Influencing', 'Persuasion',
            'Consensus Building',
            'Decision Making', 'Problem Solving',
            'Critical Thinking', 'Analytical Thinking',
            'Logical Thinking', 'Systems Thinking',
            'Strategic Thinking', 'Creative Thinking',
            'Design Thinking', 'Computational Thinking',
            'Abstract Thinking', 'Conceptual Thinking',
            'Lateral Thinking', 'Root Cause Analysis',
            'Troubleshooting Mindset', 'Judgment',
            'Sound Judgment',
            'Attention to Detail', 'Observation', 'Accuracy',
            'Quality Focus', 'Quality Mindset',
            'Curiosity', 'Continuous Learning',
            'Learning Agility', 'Growth Mindset',
            'Adaptability', 'Flexibility', 'Resilience',
            'Persistence', 'Perseverance',
            'Initiative', 'Proactivity', 'Self-Motivation',
            'Self-Discipline', 'Accountability', 'Ownership',
            'Responsibility', 'Reliability', 'Dependability',
            'Integrity', 'Professionalism', 'Work Ethic',
            'Ethical Judgment', 'Trustworthiness',
            'Time Management', 'Prioritization', 'Planning',
            'Organization', 'Scheduling', 'Multitasking',
            'Task Management', 'Goal Setting', 'Focus',
            'Concentration', 'Deadline Management',
            'Workload Management', 'Resource Management',
            'Stress Management', 'Pressure Management',
            'Change Management', 'Change Adaptability',
            'Ambiguity Tolerance',
            'Risk Awareness', 'Risk Management',
            'Strategic Planning', 'Tactical Planning',
            'Execution', 'Follow-through',
            'Project Coordination', 'Project Leadership',
            'Meeting Facilitation', 'Workshop Facilitation',
            'Facilitation',
            'Agile Mindset', 'Scrum Collaboration',
            'Kanban Mindset', 'Lean Thinking',
            'Continuous Improvement',
            'Customer Focus', 'Customer Service',
            'Client Management', 'Client Communication',
            'Customer Empathy', 'Stakeholder Management',
            'Expectation Management',
            'Requirements Clarification', 'Needs Analysis',
            'Feedback', 'Giving Feedback',
            'Receiving Feedback', 'Constructive Feedback',
            'Peer Review', 'Open-Mindedness',
            'Receptiveness to Feedback',
            'Knowledge Sharing', 'Documentation Mindset',
            'Innovation', 'Creativity', 'Ideation',
            'Brainstorming', 'Experimentation',
            'Entrepreneurial Thinking',
            'Business Acumen', 'Commercial Awareness',
            'Product Thinking', 'User-Centric Thinking',
            'Customer-Centric Thinking',
            'Data-Driven Decision Making',
            'Evidence-Based Decision Making',
            'Outcome Orientation', 'Results Orientation',
            'Process Improvement', 'Process Thinking',
            'Problem Framing', 'Research Skills',
            'Information Gathering', 'Information Synthesis',
            'Sensemaking', 'Pattern Recognition',
            'Prioritizing Trade-offs', 'Trade-off Analysis',
            'Decision Ownership', 'Crisis Management',
            'Incident Leadership', 'Calm Under Pressure',
            'Composure', 'Assertiveness', 'Diplomacy',
            'Tact', 'Professional Courtesy',
            'Inclusivity', 'Diversity Awareness',
            'Accessibility Awareness', 'Psychological Safety',
            'Inclusive Leadership', 'Community Building',
            'AI Literacy', 'Digital Fluency',
            'Security Awareness', 'Privacy Awareness',
            'Collaboration Across Time Zones',
            'Cross-time-zone Collaboration',
            'Remote Work Discipline',
            'Asynchronous Communication',
            'Meeting Management', 'Email Etiquette',
            'Professional Writing', 'Report Writing',
            'Proposal Writing', 'Documentation',
            'Note Taking',
            'Interviewing', 'Questioning Skills',
            'Socratic Questioning', 'Active Learning',
            'Teaching', 'Training', 'Knowledge Transfer',
            'Peer Learning',
            'Self-Reflection', 'Self-Management',
            'Career Management', 'Personal Development',
            'Resourcefulness', 'Independence', 'Autonomy',
            'Adaptability to Technology',
            'Technology Awareness', 'Ethical Awareness',
            'Research Mindset', 'Experimental Mindset',
            'Hypothesis Testing', 'Systems Perspective',
            'Big-Picture Thinking', 'Detail Orientation',
            'Context Switching', 'Work Prioritization',
            'Task Estimation', 'Effort Estimation',
            'Expectation Setting', 'Scope Management',
            'Boundary Setting', 'Decision Facilitation',
            'Stakeholder Alignment', 'Team Alignment',
            'Vision Communication', 'Goal Alignment',
            'Conflict De-escalation',
            'Cross-Team Coordination',
            'Cross-Department Collaboration',
            'Partner Management', 'Vendor Management',
            'Supplier Communication', 'Community Engagement',
            'Customer Advocacy', 'User Advocacy',
            'Decision Making Under Uncertainty',
            'Prioritization Under Uncertainty',
            'Learning from Failure', 'Deep Work',
            'Ownership Mindset'
        ]
    };

    function parseSkillTokens(rawInput) {
        if (!rawInput || typeof rawInput !== 'string') return [];
        return rawInput
            .split(/[,;\n\r\t•]+/)
            .map(token => token.trim().replace(/^[-*•\d.)]\s*/, ''))
            .filter(token => token.length > 0 && token.length <= 80);
    }

    function addSkillsBulk(container, cat, rawValue) {
        const tokens = parseSkillTokens(rawValue);
        if (tokens.length === 0) return;

        let skills = ResumeStore.get('skills') || [];
        const existingInCat = new Set(
            skills.filter(s => matchCategory(s.category, cat))
                  .map(s => s.name.trim().toLowerCase())
        );

        const canonicalCat = getCanonicalCategory(cat);

        let addedCount = 0;
        tokens.forEach(token => {
            const lower = token.toLowerCase();
            if (!existingInCat.has(lower)) {
                existingInCat.add(lower);
                skills.push({
                    id: ResumeStore.generateId('skill'),
                    name: token,
                    category: canonicalCat,
                    proficiency: 5,
                    sort_order: skills.length
                });
                addedCount++;
            }
        });

        if (addedCount > 0) {
            ResumeStore.set('skills', skills);
            render(container, cat);
        }
    }

    function removeSkillById(container, skillId, focusCat) {
        let skills = ResumeStore.get('skills') || [];
        skills = skills.filter(s => s.id !== skillId);
        ResumeStore.set('skills', skills);
        render(container, focusCat);
    }

    function removeLastSkillInCategory(container, cat) {
        let skills = ResumeStore.get('skills') || [];
        const catSkills = skills.filter(s => matchCategory(s.category, cat));
        if (catSkills.length === 0) return;
        const lastSkill = catSkills[catSkills.length - 1];
        removeSkillById(container, lastSkill.id, cat);
    }

    function render(container, focusCategory = null) {
        if (!container) return;

        // Clean up any existing Sortable instances before replacing HTML
        container.querySelectorAll('.tags-input-container').forEach(cont => {
            if (cont.sortableInstance) {
                try { cont.sortableInstance.destroy(); } catch (e) {}
            }
        });

        const skills = ResumeStore.get('skills') || [];

        // Ensure every skill has an ID
        skills.forEach(s => {
            if (!s.id) s.id = ResumeStore.generateId('skill');
        });

        const sortedSkills = [...skills].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

        // Detect any custom non-standard categories in skills
        const extraCats = [];
        sortedSkills.forEach(s => {
            if (s.category) {
                const isStd = CATEGORIES.some(cat => matchCategory(s.category, cat.id));
                if (!isStd) {
                    const cleanCat = String(s.category).trim().replace(/[:]+$/, '');
                    if (cleanCat && !extraCats.some(ec => ec.id.toLowerCase() === cleanCat.toLowerCase())) {
                        extraCats.push({
                            id: cleanCat,
                            label: cleanCat,
                            canonical: cleanCat
                        });
                    }
                }
            }
        });

        const allCategories = [...CATEGORIES, ...extraCats];

        container.innerHTML = `
            <h2 class="form-section-title">Skills</h2>
            <p class="form-section-subtitle">Add skills grouped by category. Type or paste multiple skills (comma, semicolon, or newline separated). Press Backspace to remove last skill. Click ✕ to remove any skill immediately.</p>
            ${allCategories.map(cat => {
                const catSkills = sortedSkills.filter(s => matchCategory(s.category, cat.id));
                const preloaded = PRELOADED_SKILLS[cat.id] || [];
                const existingNames = new Set(catSkills.map(s => s.name.trim().toLowerCase()));
                const suggestions = preloaded.filter(name => !existingNames.has(name.toLowerCase())).slice(0, 10);

                return `
                <div class="form-group skill-category-group" style="margin-bottom: var(--space-5);">
                    <label class="form-label" style="font-weight: 600;">${sanitizeHTML(cat.label)}</label>
                    <div class="tags-input-container" id="skills-${escapeAttr(cat.id)}" data-category="${escapeAttr(cat.id)}">
                        ${catSkills.map(s => `
                            <span class="tag tag-primary tag-removable" data-id="${escapeAttr(s.id)}" data-name="${escapeAttr(s.name)}" data-cat="${escapeAttr(cat.id)}">
                                ${sanitizeHTML(s.name)}
                                <span class="tag-remove" data-id="${escapeAttr(s.id)}" data-cat="${escapeAttr(cat.id)}" role="button" aria-label="Remove ${escapeAttr(s.name)}" title="Remove skill">✕</span>
                            </span>
                        `).join('')}
                        <input type="text" class="skill-input" data-category="${escapeAttr(cat.id)}" placeholder="Type or paste skills...">
                    </div>
                    <div class="skill-suggestions-wrapper" id="suggestions-wrapper-${escapeAttr(cat.id)}">
                        ${renderSuggestionsHtml(cat.id, suggestions)}
                    </div>
                </div>`;
            }).join('')}
        `;

        initSmoothDragDrop(container);
        bindEvents(container);

        if (focusCategory) {
            const input = container.querySelector(`.skill-input[data-category="${focusCategory}"]`);
            if (input) {
                input.focus();
                input.selectionStart = input.selectionEnd = input.value.length;
            }
        }
    }

    function renderSuggestionsHtml(catId, suggestions) {
        if (!suggestions || suggestions.length === 0) return '';
        return `
            <div class="skill-suggestions" style="margin-top: 6px; display: flex; flex-wrap: wrap; gap: 5px; align-items: center;">
                <span style="font-size: 11px; color: var(--color-gray-500); margin-right: 2px;">Popular:</span>
                ${suggestions.map(sug => `
                    <button type="button" class="btn-skill-suggestion" data-category="${catId}" data-value="${escapeAttr(sug)}" style="font-size: 11px; padding: 3px 9px; border-radius: 12px; border: 1px dashed var(--color-gray-300); background: var(--color-gray-50); color: var(--color-gray-700); cursor: pointer; transition: all 0.15s ease;">
                        + ${sanitizeHTML(sug)}
                    </button>
                `).join('')}
            </div>
        `;
    }

    function updateLiveSuggestions(container, inputEl) {
        const cat = inputEl.dataset.category;
        const query = inputEl.value.trim().toLowerCase();
        const wrapper = container.querySelector(`#suggestions-wrapper-${cat}`);
        if (!wrapper) return;

        const skills = ResumeStore.get('skills') || [];
        const existingNames = new Set(
            skills.filter(s => matchCategory(s.category, cat))
                  .map(s => s.name.trim().toLowerCase())
        );

        const preloaded = PRELOADED_SKILLS[cat] || [];
        let filtered;
        if (!query) {
            filtered = preloaded.filter(s => !existingNames.has(s.toLowerCase())).slice(0, 10);
        } else {
            filtered = preloaded.filter(s => !existingNames.has(s.toLowerCase()) && s.toLowerCase().includes(query)).slice(0, 12);
        }

        wrapper.innerHTML = renderSuggestionsHtml(cat, filtered);
    }

    function bindEvents(container) {
        // Prevent duplicate listener binding on container across re-renders
        if (container._skillsEventsBound) return;
        container._skillsEventsBound = true;

        // Keydown handler: Enter, Comma, and BACKSPACE to delete exactly one skill
        container.addEventListener('keydown', (e) => {
            if (!e.target.classList.contains('skill-input')) return;
            const input = e.target;
            const cat = input.dataset.category;

            // ENTER or COMMA -> Add skill
            if (e.key === 'Enter' || e.key === ',') {
                e.preventDefault();
                e.stopPropagation();
                const val = input.value;
                input.value = '';
                addSkillsBulk(container, cat, val);
                return;
            }

            // BACKSPACE on empty input -> Delete ONLY ONE skill in this category
            if (e.key === 'Backspace' && input.value === '' && input.selectionStart === 0 && input.selectionEnd === 0) {
                e.preventDefault();
                e.stopPropagation();
                removeLastSkillInCategory(container, cat);
                return;
            }
        });

        // Live input typing -> update suggestion pills dynamically
        container.addEventListener('input', (e) => {
            if (e.target.classList.contains('skill-input')) {
                updateLiveSuggestions(container, e.target);
            }
        });

        // Paste handler: handles delimiters immediately
        container.addEventListener('paste', (e) => {
            if (e.target.classList.contains('skill-input')) {
                const pasteText = (e.clipboardData || window.clipboardData)?.getData('text');
                if (pasteText && /[,;\n\r\t•]/.test(pasteText)) {
                    e.preventDefault();
                    const cat = e.target.dataset.category;
                    e.target.value = '';
                    addSkillsBulk(container, cat, pasteText);
                }
            }
        });

        // Blur handler: add any pending typed skill on focus loss
        container.addEventListener('focusout', (e) => {
            if (e.target.classList.contains('skill-input')) {
                const val = e.target.value.trim();
                const cat = e.target.dataset.category;
                if (val) {
                    e.target.value = '';
                    addSkillsBulk(container, cat, val);
                }
            }
        });

        // Pointerdown / Mousedown on remove button: stop propagation immediately so Sortable never intercepts!
        container.addEventListener('pointerdown', (e) => {
            const removeBtn = e.target.closest('.tag-remove');
            if (removeBtn) {
                e.stopPropagation();
            }
        }, true);

        container.addEventListener('mousedown', (e) => {
            const removeBtn = e.target.closest('.tag-remove');
            if (removeBtn) {
                e.stopPropagation();
            }
        }, true);

        // Click handler: removing a tag or clicking a suggestion
        container.addEventListener('click', (e) => {
            // 1. Remove tag button click
            const removeBtn = e.target.closest('.tag-remove');
            if (removeBtn) {
                e.preventDefault();
                e.stopPropagation();
                const skillId = removeBtn.dataset.id;
                const cat = removeBtn.dataset.cat;
                removeSkillById(container, skillId, cat);
                return;
            }

            // 2. Click suggestion chip
            const sugBtn = e.target.closest('.btn-skill-suggestion');
            if (sugBtn) {
                e.preventDefault();
                e.stopPropagation();
                const val = sugBtn.dataset.value;
                const cat = sugBtn.dataset.category;
                addSkillsBulk(container, cat, val);
                return;
            }
        });
    }

    function initSmoothDragDrop(container) {
        if (typeof Sortable === 'undefined') return;

        const tagContainers = container.querySelectorAll('.tags-input-container');
        
        tagContainers.forEach(cont => {
            if (cont.sortableInstance) {
                cont.sortableInstance.destroy();
            }
            
            cont.sortableInstance = new Sortable(cont, {
                group: 'skills',
                animation: 180,
                easing: "cubic-bezier(0.2, 0.8, 0.2, 1)",
                draggable: '.tag-removable',
                filter: '.skill-input, .tag-remove', // CRITICAL: Exclude remove button so clicks are never intercepted by drag!
                preventOnFilter: false,
                ghostClass: 'sortable-ghost',
                dragClass: 'sortable-drag',
                forceFallback: true,
                fallbackClass: 'sortable-fallback',
                
                onEnd: function () {
                    saveSkillOrder(container);
                    render(container);
                }
            });
        });

        function saveSkillOrder(cont) {
            const currentSkills = ResumeStore.get('skills') || [];
            const skillMap = new Map(currentSkills.map(s => [s.id, s]));
            const newSkills = [];

            cont.querySelectorAll('.tags-input-container').forEach(tagCont => {
                const catId = tagCont.dataset.category;
                const canonicalCat = getCanonicalCategory(catId);
                tagCont.querySelectorAll('.tag-removable').forEach((tag, idx) => {
                    const id = tag.dataset.id;
                    const existing = skillMap.get(id);
                    if (existing) {
                        newSkills.push({
                            ...existing,
                            category: canonicalCat,
                            sort_order: idx
                        });
                    } else {
                        newSkills.push({
                            id: id || ResumeStore.generateId('skill'),
                            name: tag.dataset.name,
                            category: canonicalCat,
                            sort_order: idx
                        });
                    }
                });
            });

            ResumeStore.set('skills', newSkills);
        }
    }

    return { render };
})();
