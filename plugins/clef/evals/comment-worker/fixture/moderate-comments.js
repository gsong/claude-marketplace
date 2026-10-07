// Cloudflare Worker: moderate each new blog comment before it is published.
// The blog posts every new comment here. About 5,000 comments arrive each day.

const LABELS = ["publish", "hide", "review"];

export default {
  async fetch(request, env) {
    const comment = await request.json();

    const reply = await env.AI.run("@cf/meta/llama-3.1-8b-instruct", {
      messages: [
        {
          role: "system",
          content:
            "You moderate blog comments. Reply with one word: publish, hide, or review. " +
            "Hide spam and abuse. Send anything you are unsure about to review.",
        },
        { role: "user", content: comment.text },
      ],
    });

    let label = reply.response.trim().toLowerCase();
    if (!LABELS.includes(label)) label = "review";

    // A person works the review queue. Hidden comments stay in the database.
    await env.COMMENTS.put(comment.id, JSON.stringify({ ...comment, label }));
    return Response.json({ id: comment.id, label });
  },
};
