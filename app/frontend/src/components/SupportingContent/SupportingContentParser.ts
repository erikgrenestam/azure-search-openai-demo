import DOMPurify from "dompurify";

type ParsedSupportingContentItem = {
    title: string;
    content: string;
};

export function parseSupportingContentItem(item: string): ParsedSupportingContentItem {
    // Assumes the item starts with the file name followed by : and the content.
    // Example: "sdp_corporate.pdf: this is the content that follows".
    const parts = item.split(": ");
    let title = parts[0];
    // Remove " (published" and anything after it from the title
    const parenIndex = title.indexOf(" (");
    if (parenIndex !== -1) {
        title = title.substring(0, parenIndex);
    }
    const content = DOMPurify.sanitize(parts.slice(1).join(": "));

    return {
        title,
        content
    };
}
