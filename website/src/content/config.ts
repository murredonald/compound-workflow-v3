import { defineCollection, z } from "astro:content";

const blog = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.coerce.date(),
    author: z.string(),
    category: z.string(),
    category_name: z.string(),
    tags: z.array(z.string()),
    locale: z.enum(["en", "nl", "fr", "de"]),
    draft: z.boolean().default(false),
  }),
});

const guides = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    topic: z.string(),
    sources: z.array(
      z.object({
        title: z.string(),
        url: z.string().url(),
        authority: z.string().optional(),
      })
    ),
    lastUpdated: z.coerce.date(),
    locale: z.enum(["en", "nl", "fr", "de"]),
  }),
});

const topics = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    template: z.enum(["tob-rate", "inheritance-tax", "treaty", "wib-article"]),
    params: z.record(z.string(), z.string()),
    sources: z.array(
      z.object({
        title: z.string(),
        url: z.string().url(),
      })
    ),
    locale: z.enum(["en", "nl", "fr", "de"]),
    relatedGuide: z.string().optional(),
  }),
});

const glossary = defineCollection({
  type: "content",
  schema: z.object({
    term: z.string(),
    termSlug: z.string(),
    short: z.string(),
    category: z.enum(["tax-law", "ai-ml", "ai-regulation", "search", "business"]),
    category_name: z.string(),
    related: z.array(z.string()).default([]),
    synonyms: z.array(z.string()).default([]),
    locale: z.enum(["en", "nl", "fr", "de"]),
    draft: z.boolean().default(false),
  }),
});

export const collections = { blog, guides, topics, glossary };
