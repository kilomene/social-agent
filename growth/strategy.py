"""Per-platform organic growth playbooks (pure stdlib).

Every playbook is organic-only: consistency, hooks, niche clarity, genuine
engagement, collaboration. Nothing here touches fake engagement, botting,
or spam — those are prohibited by the ToS layer (platforms/tos.py) and by
policy/policy.yaml's prohibited list.
"""

PLAYBOOKS = {
    "tiktok": {
        "display": "TikTok",
        "cadence": "1-3 posts/day. The algorithm rewards volume + retention; "
                   "post daily at minimum while learning.",
        "pillars": [
            "Hook in the first 2 seconds (pattern interrupt, bold claim, question).",
            "One clear niche per account — the algorithm needs to know who to serve you to.",
            "Series formats (ep.1, ep.2...) to convert viewers into followers.",
            "Native sounds/trends adapted to your niche, not copied blindly.",
        ],
        "engagement_loops": [
            "Reply to comments with video replies (doubles as new content).",
            "Pin a comment asking a question to seed discussion.",
            "Duet/stitch niche-relevant videos with a genuine take.",
        ],
        "cta_patterns": [
            "Follow for part 2 (then actually post part 2).",
            "Comment your take — reply to the best ones.",
            "Save this for later (saves are a strong ranking signal).",
        ],
        "collab_tactics": [
            "Duet creators 1-3 tiers above you with added value, not just reaction.",
            "Join niche creator group chats for early engagement pods (genuine, not botted).",
        ],
        "metrics_that_matter": ["avg watch time %", "completion rate",
                                "shares/saves per view", "follower conversion per video"],
    },
    "youtube": {
        "display": "YouTube",
        "cadence": "1-2 videos/week long-form + 3-5 Shorts/week. Consistency beats bursts.",
        "pillars": [
            "Packaging first: title + thumbnail decide 80% of performance. Never publish weak packaging.",
            "First 30 seconds must pay off the title's promise — no slow intros.",
            "One video = one idea, one viewer, one promise.",
            "Retention editing: cut dead air, change visuals every 3-8 seconds.",
        ],
        "engagement_loops": [
            "Pinned comment with a question; heart + reply to early comments.",
            "End screens pointing to the next logical video (session time).",
            "Community tab polls between uploads to keep the audience warm.",
        ],
        "cta_patterns": [
            "Subscribe for the next video in this series (name the series).",
            "Comment with your result/question — reply to seed discussion.",
        ],
        "collab_tactics": [
            "Collab videos with adjacent-niche channels of similar size.",
            "Guest appearances / shoutout swaps with genuine overlap.",
        ],
        "metrics_that_matter": ["click-through rate (CTR)", "average view duration",
                                "subscriber conversion per video", "returning viewers"],
        "note": "See platforms/youtube/growth.md and `youtube preflight` for the "
                "quality gate (resolution, audio, hooks, title, thumbnail).",
    },
    "x": {
        "display": "X",
        "cadence": "3-8 posts/day mixing originals, replies, and quote-posts. "
                   "Replies are the fastest growth lever.",
        "pillars": [
            "One strong opinion per post — bland posts get no distribution.",
            "Reply to large accounts in your niche with genuinely good takes (early).",
            "Threads for depth; single posts for reach.",
            "Your bio + pinned post must convert profile visitors in 5 seconds.",
        ],
        "engagement_loops": [
            "Reply to every genuine reply on your posts in the first hour.",
            "Quote-post instead of retweet when you have something to add.",
            "Weekly recurring format (e.g. Friday breakdown) to build habit.",
        ],
        "cta_patterns": [
            "Follow for daily breakdowns on <niche>.",
            "Repost if this helped someone you know.",
            "Bookmark + follow for part 2.",
        ],
        "collab_tactics": [
            "Reply-guy strategy on 10-20 target accounts (genuine value only).",
            "Spaces participation in niche rooms.",
        ],
        "metrics_that_matter": ["profile visits per post", "follows per 1k impressions",
                                "reply rate", "bookmarks"],
        "note": "X's terms prohibit non-API automation outright (see platforms/x/terms.md); "
                "this tool drafts and proposes only — all posting happens in a real session.",
    },
    "instagram": {
        "display": "Instagram",
        "cadence": "1 reel/day + 3-5 stories/day. Reels drive discovery; stories drive loyalty.",
        "pillars": [
            "Reels: hook in 1 second, captions with keywords (search matters now).",
            "Carousels for depth/saves; reels for reach.",
            "Aesthetic consistency so your grid converts profile visitors.",
            "Stories daily: polls, questions, behind-the-scenes.",
        ],
        "engagement_loops": [
            "Reply to comments with genuine responses, not emojis.",
            "Story stickers (polls/questions) to boost story ranking.",
            "Collab posts with adjacent creators (shared audience).",
        ],
        "cta_patterns": [
            "Follow for daily <niche> reels.",
            "Save this for later / share with someone who needs it.",
            "Comment <word> and I'll send the link/guide.",
        ],
        "collab_tactics": [
            "Instagram Collabs feature: co-author reels with similar-size creators.",
            "Shoutout swaps in stories with genuine overlap.",
        ],
        "metrics_that_matter": ["reach (non-followers %)", "saves + shares per reel",
                                "story completion", "follows per reel"],
    },
    "facebook": {
        "display": "Facebook",
        "cadence": "1 post/day + 3-5 stories/week. Groups are the growth engine.",
        "pillars": [
            "Own or co-run a niche Facebook Group — groups out-distribute pages.",
            "Native video + reels get priority in feed ranking.",
            "Conversation-starting posts (questions, opinions) over links.",
        ],
        "engagement_loops": [
            "Reply to group comments to keep threads alive.",
            "Weekly live or AMA in your group.",
            "Cross-post reels to Facebook for extra distribution.",
        ],
        "cta_patterns": [
            "Join the free group for daily <niche> help.",
            "Follow the page for the next part.",
        ],
        "collab_tactics": [
            "Partner with group admins for pinned posts / events.",
            "Co-host lives with adjacent creators.",
        ],
        "metrics_that_matter": ["group growth", "post reach", "meaningful comments",
                                "page follows per post"],
    },
    "reddit": {
        "display": "Reddit",
        "cadence": "Value-first: comment daily, post 2-4x/week across niche subreddits.",
        "pillars": [
            "Give 10x before you ask once — Reddit punishes self-promotion.",
            "Become a recognized helpful regular in 2-3 subreddits, not a drive-by poster.",
            "Follow each subreddit's self-promo rules exactly (usually 9:1 or 10:1).",
            "Long, genuinely useful comments outperform posts for karma and trust.",
        ],
        "engagement_loops": [
            "Answer new questions early in your niche subreddits.",
            "AMA once you have credibility.",
            "Link your content only where it directly answers the question.",
        ],
        "cta_patterns": [
            "Soft CTAs only: 'I made a full breakdown on this on my YT if helpful.'",
            "Never beg for upvotes/follows — it backfires and breaks rules.",
        ],
        "collab_tactics": [
            "Mod-approved collaborations / AMAs.",
            "Cross-post genuinely useful content between related subs.",
        ],
        "metrics_that_matter": ["karma growth", "comment upvote ratio",
                                "profile follows", "referral clicks"],
        "note": "Automated upvoting is vote manipulation and is prohibited "
                "(see platforms/reddit/terms.md). This tool never upvotes.",
    },
}


def list_platforms():
    return sorted(PLAYBOOKS)


def playbook(platform):
    """Return the growth playbook dict for a platform (KeyError if unknown)."""
    return PLAYBOOKS[platform]
