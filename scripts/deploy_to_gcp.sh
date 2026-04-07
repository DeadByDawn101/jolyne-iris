#!/bin/bash
# deploy_to_gcp.sh — Push Iris XMCP activities to GCP ravenx-qa-core-1
# Run from: ~/Projects/jolyne-iris/
# Usage: ./scripts/deploy_to_gcp.sh

set -e

GCP_HOST="ravenx@34.182.110.4"
GCP_KEY="$HOME/.ssh/ravenx_gcp_qa"
REMOTE_ACTIVITIES="/opt/ravenx/pippin/my_digital_being/activities"
REMOTE_WIKI="/opt/ravenx/data/jolyne/iris-wiki"

echo "🖤 Deploying Iris XMCP activities to GCP..."

# 1. Copy new activities
echo "📤 Uploading activities..."
scp -i "$GCP_KEY" \
  activities/activity_xmcp_context.py \
  activities/activity_xmcp_post_generator.py \
  activities/activity_xurl_post.py \
  activities/activity_xurl_engage.py \
  "$GCP_HOST:$REMOTE_ACTIVITIES/"

# 2. Create iris-wiki dirs on GCP
echo "📁 Creating iris-wiki directories..."
ssh -i "$GCP_KEY" "$GCP_HOST" "
  mkdir -p $REMOTE_WIKI/{market,community,posts,sources}
  echo '# Iris Wiki — Activity Log' > $REMOTE_WIKI/log.md
  echo '' >> $REMOTE_WIKI/log.md
  echo 'Append-only. Seeded on deploy.' >> $REMOTE_WIKI/log.md
"

# 3. Verify xurl is available on GCP
echo "🔍 Checking xurl on GCP..."
ssh -i "$GCP_KEY" "$GCP_HOST" "which xurl && xurl --version 2>/dev/null || echo '⚠️  xurl not found on GCP — install needed'"

# 4. Restart Pippin
echo "🔄 Restarting pippin-jolyne..."
ssh -i "$GCP_KEY" "$GCP_HOST" "sudo systemctl restart pippin-jolyne.service && sleep 3 && sudo systemctl status pippin-jolyne.service | head -20"

echo ""
echo "✅ Deploy complete!"
echo ""
echo "📋 Next: run xurl auth on GCP if not done:"
echo "  ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4"
echo "  xurl auth apps add"
echo "  xurl auth oauth2"
echo ""
echo "📊 Watch logs:"
echo "  ssh -i ~/.ssh/ravenx_gcp_qa ravenx@34.182.110.4 'journalctl -u pippin-jolyne -f'"
