// =============================================================================
// Live ATS Keyword Matcher & Resume Scorer
// =============================================================================

const AtsScanner = (() => {
    // Common English stop words to filter out
    const STOP_WORDS = new Set([
        'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t',
        'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by',
        'can', 'can\'t', 'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing',
        'don\'t', 'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t',
        'have', 'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers',
        'herself', 'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if',
        'in', 'into', 'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most',
        'mustn\'t', 'my', 'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other',
        'ought', 'our', 'ours', 'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d',
        'she\'ll', 'she\'s', 'should', 'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the',
        'their', 'theirs', 'them', 'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d',
        'they\'ll', 'they\'re', 'they\'ve', 'this', 'those', 'through', 'to', 'too', 'under', 'until',
        'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d', 'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t',
        'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s', 'which', 'while', 'who', 'who\'s', 'whom',
        'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you', 'you\'d', 'you\'ll', 'you\'re',
        'you\'ve', 'your', 'yours', 'yourself', 'yourselves', 'will', 'also', 'etc', 'including', 'responsible',
        'experience', 'work', 'working', 'ability', 'skills', 'role', 'team', 'years', 'job', 'requirements',
        'duties', 'responsibilities', 'qualifications', 'preferred', 'must', 'candidate', 'ideal', 'looking'
    ]);

    // Known tech terms and multi-word phrases to preserve
    const PRESERVED_PHRASES = [
        'c++', 'c#', '.net', 'node.js', 'vue.js', 'react.js', 'next.js', 'ci/cd',
        'machine learning', 'deep learning', 'data science', 'full stack', 'front end', 'back end',
        'system design', 'rest api', 'graphql api', 'cloud computing', 'distributed systems',
        'microservices', 'unit testing', 'test driven development', 'object oriented',
        'agile methodology', 'scrum master', 'product management', 'customer discovery',
        'user experience', 'information security', 'relational database', 'cross functional'
    ];

    /**
     * Extracts full searchable text corpus from ResumeStore data.
     */
    function extractResumeCorpus(resumeData) {
        const d = resumeData || {};
        const parts = [
            d.first_name,
            d.last_name,
            d.professional_title,
            d.summary,
            (d.skills || []).map(s => s.name).join(' '),
            (d.experience || []).map(e => `${e.position} ${e.company} ${e.description}`).join(' '),
            (d.education || []).map(e => `${e.degree} ${e.field_of_study} ${e.institution} ${e.description}`).join(' '),
            (d.projects || []).map(p => `${p.title} ${p.description} ${(p.technologies || []).join(' ')}`).join(' '),
            (d.certifications || []).map(c => `${c.name} ${c.issuer}`).join(' '),
            (d.awards || []).map(a => `${a.title} ${a.description}`).join(' '),
            (d.volunteer || []).map(v => `${v.organization} ${v.role} ${v.description}`).join(' ')
        ];
        return parts.filter(Boolean).join(' ').toLowerCase();
    }

    /**
     * Tokenizes and extracts frequency of meaningful keywords & preserved phrases from raw text.
     */
    function extractKeywords(text) {
        if (!text || typeof text !== 'string') return new Map();
        const lower = text.toLowerCase();
        const keywordMap = new Map();

        // Check for preserved phrases first
        PRESERVED_PHRASES.forEach(phrase => {
            const regex = new RegExp(`\\b${phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}\\b`, 'gi');
            const matches = lower.match(regex);
            if (matches && matches.length > 0) {
                keywordMap.set(phrase, matches.length);
            }
        });

        // Tokenize words (allowing single tech symbols like c++, c#, .net)
        const wordTokens = lower
            .replace(/[^\w\s\+\#\.\/\-]/g, ' ')
            .split(/\s+/)
            .map(w => w.trim().replace(/^[\.\/\-]+|[\.\/\-]+$/g, ''))
            .filter(w => w.length > 1 && !STOP_WORDS.has(w) && !/^\d+$/.test(w));

        wordTokens.forEach(word => {
            // If already counted in preserved phrase, skip double-counting single subwords if desired
            const count = keywordMap.get(word) || 0;
            keywordMap.set(word, count + 1);
        });

        return keywordMap;
    }

    /**
     * Compares a job description string against the active resume state.
     */
    function analyze(jobDescription, resumeData) {
        if (!jobDescription || !jobDescription.trim()) {
            return null;
        }

        const resumeCorpus = extractResumeCorpus(resumeData || ResumeStore.getResumeData());
        const jdKeywords = extractKeywords(jobDescription);

        if (jdKeywords.size === 0) {
            return {
                score: 0,
                matched: [],
                missing: [],
                totalKeywords: 0,
                tips: ['Please provide a more detailed job description to extract relevant keywords.']
            };
        }

        // Sort JD keywords by frequency (importance)
        const sortedJdEntries = Array.from(jdKeywords.entries())
            .sort((a, b) => b[1] - a[1]);

        // Top prominent keywords from JD (up to 30)
        const topJdKeywords = sortedJdEntries.slice(0, 30);

        const matched = [];
        const missing = [];

        topJdKeywords.forEach(([kw, freq]) => {
            // Check if present in resume corpus
            const escaped = kw.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const regex = new RegExp(`\\b${escaped}\\b`, 'i');
            if (regex.test(resumeCorpus)) {
                matched.push({ keyword: kw, count: freq });
            } else {
                missing.push({ keyword: kw, count: freq });
            }
        });

        const totalTop = topJdKeywords.length;
        const rawScore = totalTop > 0 ? Math.round((matched.length / totalTop) * 100) : 0;

        // Generate actionable tips
        const tips = [];
        if (missing.length > 0) {
            const topMissingNames = missing.slice(0, 5).map(m => `"${m.keyword}"`).join(', ');
            tips.push(`Add high-frequency terms from the job posting: ${topMissingNames}.`);
        }

        const data = resumeData || ResumeStore.getResumeData();
        const expDesc = (data.experience || []).map(e => e.description || '').join(' ');
        const hasNumbers = /\d+%|\d+\+|\$\d+|\b\d+\b/.test(expDesc);
        if (!hasNumbers) {
            tips.push('Quantify your experience with measurable metrics (e.g. "improved by 25%", "managed $100k budget").');
        }

        if (!data.summary || data.summary.trim().length < 80) {
            tips.push('Expand your professional summary to include your target job title and core specializations.');
        }

        if ((data.skills || []).length < 6) {
            tips.push('List at least 8–12 relevant skills in your Skills section to pass automated recruiter screeners.');
        }

        let rating = 'Needs Work';
        let ratingColor = 'var(--color-danger, #ef4444)';
        if (rawScore >= 80) {
            rating = 'Excellent Match';
            ratingColor = 'var(--color-success, #10b981)';
        } else if (rawScore >= 65) {
            rating = 'Strong Match';
            ratingColor = 'var(--color-accent, #2563eb)';
        } else if (rawScore >= 45) {
            rating = 'Moderate Match';
            ratingColor = 'var(--color-warning, #f59e0b)';
        }

        return {
            score: rawScore,
            rating,
            ratingColor,
            matched,
            missing,
            totalKeywords: totalTop,
            tips
        };
    }

    return {
        analyze,
        extractKeywords,
        extractResumeCorpus
    };
})();
