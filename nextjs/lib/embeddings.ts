import OpenAI from 'openai'

let openaiClient: OpenAI | null = null

function getOpenAI(): OpenAI {
  if (!openaiClient) {
    openaiClient = new OpenAI({ apiKey: process.env.OPENAI_API_KEY! })
  }
  return openaiClient
}

/**
 * Generate a 1536-dim embedding vector using OpenAI text-embedding-3-small.
 * Falls back to a deterministic hash-based vector if OPENAI_API_KEY is not set,
 * which is suitable for development but not for semantic search in production.
 */
export async function generateEmbedding(text: string): Promise<number[]> {
  if (!process.env.OPENAI_API_KEY) {
    return hashEmbedding(text)
  }

  try {
    const openai = getOpenAI()
    const response = await openai.embeddings.create({
      model: 'text-embedding-3-small',
      input: text.slice(0, 8000),
    })
    return response.data[0].embedding
  } catch (err) {
    console.error('Embedding error, falling back to hash:', err)
    return hashEmbedding(text)
  }
}

/**
 * Deterministic hash-based pseudo-embedding. Consistent across calls for the same input.
 * Used as fallback when OpenAI API key is not available.
 */
function hashEmbedding(text: string): number[] {
  const dim = 1536
  const vec = new Array<number>(dim).fill(0)
  const normalized = text.toLowerCase().trim()

  for (let i = 0; i < normalized.length; i++) {
    const charCode = normalized.charCodeAt(i)
    vec[i % dim] += charCode / 255
    vec[(i * 7 + 13) % dim] += Math.sin(charCode * 0.1) * 0.5
    vec[(i * 31 + 97) % dim] += Math.cos(charCode * 0.05) * 0.5
  }

  // L2 normalize
  const norm = Math.sqrt(vec.reduce((sum, x) => sum + x * x, 0))
  return vec.map((x) => (norm > 0 ? x / norm : 0))
}

/**
 * Search the knowledge base using vector similarity via Supabase RPC.
 * Falls back to a text-based search if embeddings are unavailable.
 */
export async function searchKnowledge(
  supabaseAdmin: ReturnType<typeof import('./supabase-server').createAdminClient>,
  query: string,
  matchCount = 5
): Promise<Array<{ id: string; category: string; title: string; content: string; tags: string[]; similarity: number }>> {
  try {
    const embedding = await generateEmbedding(query)
    const { data, error } = await supabaseAdmin.rpc('match_knowledge', {
      query_embedding: embedding,
      match_threshold: 0.5,
      match_count: matchCount,
    })
    if (error) {
      console.error('Vector search error, falling back to text search:', error)
      return fallbackTextSearch(supabaseAdmin, query, matchCount)
    }
    return data || []
  } catch (err) {
    console.error('Knowledge search error:', err)
    return fallbackTextSearch(supabaseAdmin, query, matchCount)
  }
}

async function fallbackTextSearch(
  supabaseAdmin: ReturnType<typeof import('./supabase-server').createAdminClient>,
  query: string,
  matchCount: number
): Promise<Array<{ id: string; category: string; title: string; content: string; tags: string[]; similarity: number }>> {
  const terms = query.split(' ').filter(Boolean).slice(0, 5).join(' | ')
  const { data } = await supabaseAdmin
    .from('knowledge_base')
    .select('id, category, title, content, tags')
    .eq('active', true)
    .textSearch('content', terms, { type: 'websearch' })
    .limit(matchCount)

  return (data || []).map((row) => ({ ...row, similarity: 0.7 }))
}
