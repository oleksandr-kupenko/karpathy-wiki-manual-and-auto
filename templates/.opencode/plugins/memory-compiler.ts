import type { Plugin } from "@opencode-ai/plugin"
import { existsSync, readFileSync, writeFileSync, mkdirSync } from "node:fs"
import { join, resolve } from "node:path"
import { spawn } from "node:child_process"

const MAX_CONTEXT = 20_000
const MAX_LOG_LINES = 30
const MAX_TURNS = 30
const MAX_FLUSH_CHARS = 15_000

export default (async ({ client, directory }) => {
  const compilerDir = join(resolve(directory), "karpathy-wiki-manual-and-auto")
  if (!existsSync(compilerDir)) return {}

  const vaultDir = join(resolve(directory), process.env.WIKI_VAULT_DIR || "obsidian-vault")
  const dailyDir = join(vaultDir, "daily")
  const scriptsDir = join(compilerDir, "scripts")

  function read(path: string): string {
    return existsSync(path) ? readFileSync(path, "utf-8") : ""
  }

  function readRecentLog(): string {
    const { readdirSync } = require("node:fs") as typeof import("node:fs")
    for (let i = 0; i < 2; i++) {
      const d = new Date()
      d.setDate(d.getDate() - i)
      const dateStr = d.toISOString().split("T")[0]
      // Collect all daily files for this date: YYYY-MM-DD.md, YYYY-MM-DD_claude.md, etc.
      let files: string[] = []
      try {
        files = readdirSync(dailyDir)
          .filter((f: string) => f.startsWith(dateStr) && f.endsWith(".md"))
          .sort()
          .map((f: string) => join(dailyDir, f))
      } catch {}
      if (files.length > 0) {
        const allLines = files.flatMap((f: string) => read(f).split("\n"))
        return allLines.slice(-MAX_LOG_LINES).join("\n")
      }
    }
    return "(no recent daily log)"
  }

  function buildContext(): string {
    const indexFile = join(vaultDir, "index.md")
    const parts = [
      `## Wiki Index\n\n${existsSync(indexFile) ? read(indexFile) : "(empty)"}`,
      `## Recent Daily Log\n\n${readRecentLog()}`,
    ]
    let ctx = parts.join("\n\n---\n\n")
    if (ctx.length > MAX_CONTEXT) ctx = ctx.slice(0, MAX_CONTEXT) + "\n\n...(truncated)"
    return ctx
  }

  function spawnFlush(contextFile: string, sessionId: string) {
    const flushScript = join(scriptsDir, "flush.py")
    if (!existsSync(flushScript)) return
    spawn(
      "uv",
      ["run", "--directory", compilerDir, "python", flushScript, contextFile, sessionId, "opencode"],
      { detached: true, stdio: "ignore" }
    ).unref()
  }

  function extractMessages(messages: any[]): string {
    const turns = messages
      .filter((m: any) => m.role === "user" || m.role === "assistant")
      .map((m: any) => {
        let c = m.content ?? ""
        if (Array.isArray(c)) {
          c = c
            .filter((b: any) => typeof b === "string" || b?.type === "text")
            .map((b: any) => (typeof b === "string" ? b : b.text ?? ""))
            .join("\n")
        }
        if (typeof c !== "string" || !c.trim()) return ""
        return `**${m.role === "user" ? "User" : "Assistant"}:** ${c.trim()}\n`
      })
      .filter(Boolean)

    let ctx = turns.slice(-MAX_TURNS).join("\n")
    if (ctx.length > MAX_FLUSH_CHARS) {
      ctx = ctx.slice(-MAX_FLUSH_CHARS)
      const b = ctx.indexOf("\n**")
      if (b > 0) ctx = ctx.slice(b + 1)
    }
    return ctx
  }

  function writeFlushContext(sessionId: string, context: string): string {
    mkdirSync(scriptsDir, { recursive: true })
    const ts = new Date().toISOString().replace(/[-:T.Z]/g, "").slice(0, 15)
    const f = join(scriptsDir, `opencode-flush-${sessionId}-${ts}.md`)
    writeFileSync(f, context, "utf-8")
    return f
  }

  async function flushSession(sessionId: string) {
    try {
      let context = ""

      if (client?.session?.messages) {
        try {
          const res = await client.session.messages({ path: { id: sessionId } })
          const msgs =
            (res as any)?.data ?? (Array.isArray(res) ? res : [])
          if (Array.isArray(msgs) && msgs.length > 0) {
            context = extractMessages(msgs)
          }
        } catch {}
      }

      if (!context) return
      const ctxFile = writeFlushContext(sessionId, context)
      spawnFlush(ctxFile, sessionId)
    } catch {}
  }

  return {
    "experimental.session.compacting": async (_input: any, output: any) => {
      output.context.push(buildContext())
    },

    event: async ({ event }: { event: any }) => {
      if (event.type === "session.idle") {
        const sid = event.data?.id ?? event.data?.session_id ?? "unknown"
        await flushSession(sid)
      }
    },
  }
}) satisfies Plugin
