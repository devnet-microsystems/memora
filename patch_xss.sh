sed -i '' -e 's/${a.group.toUpperCase()}/${escapeHTML(a.group.toUpperCase())}/g' dashboard/templates/index.html
sed -i '' -e 's/${a.label}/${escapeHTML(a.label)}/g' dashboard/templates/index.html
sed -i '' -e 's/${item.event_date || '\''Memory'\''}/${escapeHTML(item.event_date || '\''Memory'\'')}/g' dashboard/templates/story.html
sed -i '' -e 's/${item.content}/${escapeHTML(item.content)}/g' dashboard/templates/story.html
