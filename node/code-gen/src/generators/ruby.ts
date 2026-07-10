import { CodeGenerator, getHttpMethod, operationHasPayload, resolveHref } from "./helpers.js";

// ---------------------------------------------------------------------------
// Net::HTTP  –  Ruby standard library HTTP client
// ---------------------------------------------------------------------------

export const generateRubyNetHttpCode: CodeGenerator = (ctx) => {
    const { td, affordanceKey, operation, form } = ctx;
    const href = resolveHref(form.href, td.base);
    const method = getHttpMethod(operation, form);
    const hasPayload = operationHasPayload(operation);

    const rubyHttpClass: Record<string, string> = {
        GET: "Net::HTTP::Get",
        POST: "Net::HTTP::Post",
        PUT: "Net::HTTP::Put",
        DELETE: "Net::HTTP::Delete",
        PATCH: "Net::HTTP::Patch",
    };
    const reqClass = rubyHttpClass[method] ?? `Net::HTTP::Get`;

    const payloadBlock = hasPayload
        ? `
# TODO: Replace with the actual value to send
request.content_type = "application/json"
request.body = JSON.generate({})`
        : "";

    const sslLine = href.startsWith("https") ? `http.use_ssl = true` : `http.use_ssl = false`;

    return `require "net/http"
require "uri"
require "json"

# Auto-generated code using Net::HTTP
# Operation: ${operation} on "${affordanceKey}"

uri = URI.parse("${href}")

http = Net::HTTP.new(uri.host, uri.port)
${sslLine}

request = ${reqClass}.new(uri.request_uri)
${payloadBlock}

response = http.request(request)

puts "Status: #{response.code}"
puts "${affordanceKey}: #{response.body}"
`;
};
