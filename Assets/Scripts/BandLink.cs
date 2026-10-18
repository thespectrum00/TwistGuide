using System;
using System.Globalization;
using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Threading;
using UnityEngine;

/// <summary>
/// Talks to the wristband over Wi-Fi (UDP port 4210), using the same messages as the firmware.
///
/// Band to phone, 50 times a second:  A,&lt;ms&gt;,&lt;angle deg&gt;,&lt;button 0/1&gt;,&lt;on target 0/1&gt;
/// Phone to band:                      T,&lt;target&gt;,&lt;tolerance&gt;,&lt;haptics 0/1&gt;   S   Z
///
/// Put this on an empty GameObject called "Band". The phone must be the hotspot the band joins,
/// and Player Settings > Internet Access must be set to "Require".
/// </summary>
public class BandLink : MonoBehaviour
{
    [SerializeField] int port = 4210;
    [Tooltip("Seconds without a message before the band counts as disconnected.")]
    [SerializeField] float timeoutSeconds = 1f;

    readonly object gate = new object();
    UdpClient client;
    Thread receiveThread;
    volatile bool running;

    // Written by the background thread, read on the main thread (always inside the lock).
    float angle;
    bool buttonDown;
    bool onTarget;
    long bandMillis;
    int packetCount;
    IPEndPoint bandEndPoint;

    // Main-thread bookkeeping for the connection check.
    int lastSeenCount;
    float lastSeenTime = -999f;

    /// <summary>Wrist twist in degrees, relative to the band's zero position.</summary>
    public float Angle { get { lock (gate) return angle; } }
    public bool ButtonDown { get { lock (gate) return buttonDown; } }
    /// <summary>True while the band itself judges the wrist to be inside the target.</summary>
    public bool OnTarget { get { lock (gate) return onTarget; } }
    public long BandMillis { get { lock (gate) return bandMillis; } }
    public bool Connected { get { return Time.realtimeSinceStartup - lastSeenTime < timeoutSeconds; } }
    public string BandAddress
    {
        get { lock (gate) return bandEndPoint == null ? "none yet" : bandEndPoint.Address.ToString(); }
    }

    void OnEnable()
    {
        try
        {
            client = new UdpClient(port);
        }
        catch (SocketException e)
        {
            Debug.LogError("BandLink: could not open UDP port " + port + ": " + e.Message);
            enabled = false;
            return;
        }
        running = true;
        receiveThread = new Thread(ReceiveLoop) { IsBackground = true, Name = "BandLink receive" };
        receiveThread.Start();
    }

    void OnDisable()
    {
        running = false;
        if (client != null)
        {
            client.Close();        // unblocks Receive() on the background thread
            client = null;
        }
        if (receiveThread != null)
        {
            receiveThread.Join(200);
            receiveThread = null;
        }
    }

    void Update()
    {
        int count;
        lock (gate) count = packetCount;
        if (count != lastSeenCount)
        {
            lastSeenCount = count;
            lastSeenTime = Time.realtimeSinceStartup;
        }
    }

    void ReceiveLoop()
    {
        IPEndPoint from = new IPEndPoint(IPAddress.Any, 0);
        while (running)
        {
            byte[] data;
            try
            {
                data = client.Receive(ref from);
            }
            catch (SocketException)
            {
                if (!running) break;
                continue;
            }
            catch (ObjectDisposedException)
            {
                break;
            }
            catch (NullReferenceException)
            {
                break;
            }
            HandleMessage(Encoding.ASCII.GetString(data), from);
        }
    }

    /// <summary>Parse one message from the band. Public so it can be tested without a network.</summary>
    public bool HandleMessage(string text, IPEndPoint from)
    {
        string[] parts = text.Trim().Split(',');
        if (parts.Length < 5 || parts[0] != "A")
            return false;

        long ms;
        float a;
        int b, t;
        if (!long.TryParse(parts[1], NumberStyles.Integer, CultureInfo.InvariantCulture, out ms)) return false;
        // InvariantCulture: phones set to a language that writes 12,5 instead of 12.5 still parse correctly.
        if (!float.TryParse(parts[2], NumberStyles.Float, CultureInfo.InvariantCulture, out a)) return false;
        if (!int.TryParse(parts[3], NumberStyles.Integer, CultureInfo.InvariantCulture, out b)) return false;
        if (!int.TryParse(parts[4], NumberStyles.Integer, CultureInfo.InvariantCulture, out t)) return false;

        lock (gate)
        {
            bandMillis = ms;
            angle = a;
            buttonDown = b == 1;
            onTarget = t == 1;
            packetCount++;
            if (from != null)
                bandEndPoint = new IPEndPoint(from.Address, port);   // reply to whoever is sending
        }
        return true;
    }

    /// <summary>Start guiding towards a target. Haptics off = the band stays silent (visual-only condition).</summary>
    public void SendTarget(float targetDeg, float toleranceDeg, bool haptics)
    {
        Send(string.Format(CultureInfo.InvariantCulture, "T,{0:F1},{1:F1},{2}",
            targetDeg, toleranceDeg, haptics ? 1 : 0));
    }

    /// <summary>Stop guiding; motors go quiet.</summary>
    public void SendStop() { Send("S"); }

    /// <summary>Make the wrist's current position the zero angle.</summary>
    public void SendZero() { Send("Z"); }

    void Send(string message)
    {
        IPEndPoint target;
        lock (gate) target = bandEndPoint;
        if (target == null || client == null)
        {
            Debug.LogWarning("BandLink: nothing heard from the band yet, so '" + message + "' was not sent.");
            return;
        }
        byte[] bytes = Encoding.ASCII.GetBytes(message);
        try
        {
            client.Send(bytes, bytes.Length, target);
        }
        catch (Exception e)
        {
            Debug.LogWarning("BandLink: send failed: " + e.Message);
        }
    }
}
