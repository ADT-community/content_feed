# Video Hosting Research

## Options Compared

### 1. Cloudflare Stream
- **Pricing**: $5 per 1,000 minutes stored, $1 per 1,000 minutes streamed.
- **Video size**: 30 s @ 480p ≈ 0.5 minute.
- **Cost per 1,000 views**: 0.5 min × 1,000 = 500 minutes streamed → 500/1,000 × $1 = **$0.50**.
- **African delivery**: Cloudflare has PoPs in South Africa, Kenya, Nigeria and many other African locations, giving low latency.
- **Pros**: Integrated transcoding, player, DRM support, excellent global (including Africa) edge network.
- **Cons**: Slightly higher cost than the cheapest alternative.

### 2. Bunny.net Stream
- **Pricing**: $0.01 per GB transferred, $0.02 per GB stored.
- **Video size**: 30 s @ 480p ≈ 5 MB (0.005 GB).
- **Cost per 1,000 views**: 5 MB × 1,000 = 5 GB transferred → 5 × $0.01 = **$0.05**.
- **Storage cost**: 0.005 GB × $0.02 ≈ $0.0001 (negligible).
- **African delivery**: Bunny has PoPs in Europe and a dedicated PoP in South Africa; latency is acceptable but fewer edge nodes than Cloudflare.
- **Pros**: Very low per‑view cost, simple pricing.
- **Cons**: Smaller African edge footprint, no built‑in DRM.

### 3. Self‑hosted on AWS S3 + CloudFront
- **Pricing**: S3 storage $0.023/GB‑month; CloudFront data transfer $0.085/GB (first 10 TB).
- **Video size**: 5 MB (0.005 GB).
- **Cost per 1,000 views**: 5 GB transferred → 5 × $0.085 = **$0.425**.
- **Storage cost**: 0.005 GB × $0.023 ≈ $0.0001 per month (negligible).
- **African delivery**: CloudFront has edge locations in Cape Town and Johannesburg; latency is decent but operational overhead is higher.
- **Pros**: Full control over storage and CDN, familiar AWS ecosystem.
- **Cons**: Higher cost than Bunny, more operational complexity, separate transcoding solution needed.

## Recommendation
Based on the analysis, **Cloudflare Stream** is the recommended solution. It offers a modest $0.50 cost per 1,000 views, built‑in transcoding and player features, and the most extensive African edge network, which aligns with our latency requirements for users on the continent. While Bunny.net is cheaper, the additional operational simplicity and superior African coverage of Cloudflare Stream provide better overall value for the project.
