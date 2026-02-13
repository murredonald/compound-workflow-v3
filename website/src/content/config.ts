import { defineCollection, z } from "astro:content";

const blog = defineCollection({
  type: "content",
  schema: z.object({
    title: z.string(),
    description: z.string(),
    publishDate: z.coerce.date(),
    author: z.string(),
    category: z.enum(["tax-update", "product", "insight", "guide"]),
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

export const collections = { blog, guides, topics };
