// Windows 便携启动器：资源内嵌，只在回环地址提供白名单文件。
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Net;
using System.Net.Sockets;
using System.Reflection;
using System.Text;
using System.Threading;
using System.Windows.Forms;

internal static class Launcher {
    static readonly Dictionary<string, byte[]> Files = new Dictionary<string, byte[]>(StringComparer.Ordinal);
    static TcpListener server;
    static volatile bool running;
    static string url;

    [STAThread]
    static void Main(string[] args) {
        try {
            using (Stream input = Assembly.GetExecutingAssembly().GetManifestResourceStream("game.zip"))
            using (var zip = new ZipArchive(input, ZipArchiveMode.Read)) {
                foreach (var entry in zip.Entries) {
                    using (var data = new MemoryStream()) {
                        using (var source = entry.Open()) source.CopyTo(data);
                        Files.Add("/" + entry.FullName, data.ToArray());
                    }
                }
            }
            if (!Files.ContainsKey("/index.html")) throw new InvalidDataException("Missing index.html");
            server = new TcpListener(IPAddress.Loopback, 0);
            server.Start(128);
            url = "http://127.0.0.1:" + ((IPEndPoint)server.LocalEndpoint).Port + "/";
            running = true;
            var thread = new Thread(Accept) { IsBackground = true };
            thread.Start();
            // 仅供构建验收使用，正常启动不创建日志或解压文件。
            if (args.Length == 2 && args[0] == "--serve-only") {
                File.WriteAllText(args[1], url, new UTF8Encoding(false));
                Thread.Sleep(Timeout.Infinite);
                return;
            }
            Application.EnableVisualStyles();
            var form = new Form {
                Text = "三更 · v1.0.1", ClientSize = new Size(460, 245),
                StartPosition = FormStartPosition.CenterScreen,
                FormBorderStyle = FormBorderStyle.FixedDialog, MaximizeBox = false,
                BackColor = Color.FromArgb(18, 21, 20), ForeColor = Color.FromArgb(225, 218, 199),
                Font = new Font("Microsoft YaHei UI", 10)
            };
            var info = new Label {
                Left = 24, Top = 22, Width = 410, Height = 110,
                Text = "三更 · 三个心理恐怖短篇\n\n游戏已在浏览器窗口打开。\n游玩时请保留此窗口；退出会关闭本地游戏服务。\n首次点击“开始”后启用声音，E 交互，Esc 暂停。"
            };
            var open = new Button { Text = "打开游戏", Left = 24, Top = 153, Width = 185, Height = 42 };
            var exit = new Button { Text = "退出", Left = 231, Top = 153, Width = 185, Height = 42 };
            open.Click += delegate { OpenGame(); };
            exit.Click += delegate { form.Close(); };
            form.Controls.AddRange(new Control[] { info, open, exit });
            form.Shown += delegate { OpenGame(); };
            Application.Run(form);
        } catch (Exception e) {
            MessageBox.Show("无法启动《三更》：\n" + e.Message, "三更", MessageBoxButtons.OK, MessageBoxIcon.Error);
            Environment.ExitCode = 1;
        } finally {
            running = false;
            if (server != null) server.Stop();
        }
    }

    static void OpenGame() {
        try {
            // 使用现有浏览器的应用窗口；不携带 Node 权限、不访问账号或个人文件。
            string[] candidates = {
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86), @"Microsoft\Edge\Application\msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Microsoft\Edge\Application\msedge.exe"),
                Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles), @"Google\Chrome\Application\chrome.exe")
            };
            foreach (string browser in candidates) {
                if (!File.Exists(browser)) continue;
                Process.Start(new ProcessStartInfo(browser, "--app=" + url) { UseShellExecute = true });
                return;
            }
            Process.Start(new ProcessStartInfo(url) { UseShellExecute = true });
        } catch (Exception e) {
            MessageBox.Show("请用 Edge 或 Chrome 打开：\n" + url + "\n\n" + e.Message, "打开游戏");
        }
    }

    static void Accept() {
        while (running) {
            try {
                var client = server.AcceptTcpClient();
                ThreadPool.QueueUserWorkItem(delegate { Serve(client); });
            } catch (SocketException) { if (!running) return; }
              catch (ObjectDisposedException) { return; }
        }
    }

    static void Serve(TcpClient client) {
        using (client) {
            try {
                client.ReceiveTimeout = client.SendTimeout = 5000;
                using (var stream = client.GetStream()) {
                    // 请求头上限 16 KiB，避免无限行或慢连接长期占用线程。
                    var header = new List<byte>();
                    while (header.Count < 16384) {
                        int value = stream.ReadByte();
                        if (value < 0) return;
                        header.Add((byte)value);
                        int n = header.Count;
                        if (n >= 4 && header[n-4]==13 && header[n-3]==10 && header[n-2]==13 && header[n-1]==10) break;
                    }
                    if (header.Count >= 16384) { Reply(stream, 431, "text/plain", new byte[0], false); return; }
                    string[] lines = Encoding.ASCII.GetString(header.ToArray()).Split(new[] { "\r\n" }, StringSplitOptions.None);
                    string[] request = lines[0].Split(' ');
                    if (request.Length != 3) { Reply(stream, 400, "text/plain", new byte[0], false); return; }
                    if (request[0] != "GET" && request[0] != "HEAD") { Reply(stream, 405, "text/plain", new byte[0], false); return; }
                    // 限制 Host 为本监听端口，避免 DNS rebinding 借本地服务读取资源。
                    bool hostOK = false;
                    string expectedHost = new Uri(url).Authority;
                    foreach (string line in lines)
                        if (line.StartsWith("Host:", StringComparison.OrdinalIgnoreCase))
                            hostOK = line.Substring(5).Trim().Equals(expectedHost, StringComparison.OrdinalIgnoreCase);
                    if (!hostOK) { Reply(stream, 403, "text/plain", new byte[0], false); return; }
                    string path = Uri.UnescapeDataString(request[1].Split('?')[0]);
                    if (!path.StartsWith("/") || path.Contains("..") || path.Contains("\\")) { Reply(stream, 403, "text/plain", new byte[0], false); return; }
                    if (path.EndsWith("/")) path += "index.html";
                    byte[] data;
                    if (!Files.TryGetValue(path, out data)) { Reply(stream, 404, "text/plain", new byte[0], false); return; }
                    Reply(stream, 200, Mime(path), data, request[0] == "HEAD");
                }
            } catch (IOException) { } catch (SocketException) { } catch (UriFormatException) { }
        }
    }

    static string Mime(string path) {
        switch (Path.GetExtension(path).ToLowerInvariant()) {
            case ".html": return "text/html; charset=utf-8";
            case ".js": case ".mjs": return "text/javascript; charset=utf-8";
            case ".css": return "text/css; charset=utf-8";
            case ".json": return "application/json; charset=utf-8";
            case ".glb": return "model/gltf-binary";
            case ".ogg": return "audio/ogg";
            case ".jpg": case ".jpeg": return "image/jpeg";
            case ".png": return "image/png";
            case ".svg": return "image/svg+xml";
            default: return "application/octet-stream";
        }
    }

    static void Reply(Stream stream, int code, string mime, byte[] data, bool head) {
        string status = code == 200 ? "OK" : "Error";
        byte[] header = Encoding.ASCII.GetBytes("HTTP/1.1 " + code + " " + status + "\r\nContent-Type: " + mime + "\r\nContent-Length: " + data.Length + "\r\nConnection: close\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\n\r\n");
        stream.Write(header, 0, header.Length);
        if (!head) stream.Write(data, 0, data.Length);
    }
}
