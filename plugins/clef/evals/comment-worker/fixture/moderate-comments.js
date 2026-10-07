// Cloudflare Worker: moderate each new blog comment before it is published.
// The blog saves every new comment as pending and sends it to this queue.
// About 5,000 comments arrive each day.

const LABELS = ["publish", "hide", "review"];

export default {
  async queue(batch, env) {
    for (const message of batch.messages) {
      const comment = message.body;

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

      // The blog shows a comment once its label is "publish". A person works
      // the review queue. Hidden comments stay in the database.
      await env.COMMENTS.put(comment.id, JSON.stringify({ ...comment, label }));
      message.ack();
    }
  },
};
