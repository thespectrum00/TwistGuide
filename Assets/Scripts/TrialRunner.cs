using System.Collections;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using UnityEngine;

public enum GuideCondition { Visual, Haptic, Both }

/// <summary>
/// Runs a block of trials and logs each one to a CSV file on the phone.
/// Put it on an empty GameObject called "Study".
///
/// One trial: a target angle is chosen, the band starts guiding (unless the condition is Visual),
/// the participant twists until they think the ring is aligned, then taps Confirm.
///
/// UI to wire up: buttons for StartBlock(), Confirm() and ZeroBand();
/// optionally a TMP Dropdown (Visual, Haptic, Both) calling SetCondition(int).
/// </summary>
public class TrialRunner : MonoBehaviour
{
    [Header("Links")]
    [SerializeField] BandLink band;
    [SerializeField] RingController rings;
    [Tooltip("A thin needle on the disk pointing at the target. Shown only in the Visual and Both conditions.")]
    [SerializeField] Transform targetMarker;
    [SerializeField] TMPro.TMP_Text statusLabel;

    [Header("Study settings")]
    [SerializeField] string participantId = "P01";
    [SerializeField] GuideCondition condition = GuideCondition.Visual;
    [Tooltip("Target angles in degrees. Keep them inside the wearer's comfortable wrist range.")]
    [SerializeField] float[] targets = { -60f, -40f, -20f, 20f, 40f, 60f };
    [SerializeField] float toleranceDeg = 3f;
    [SerializeField] int repetitions = 2;
    [SerializeField] float pauseBetweenTrials = 1.5f;

    readonly List<float> order = new List<float>();
    int index;
    bool running;
    float target;
    float startTime;
    int overshoots;
    int lastSign;
    bool blockActive;
    bool finished;
    float lastAbsError;
    float lastSeconds;
    float sumAbsError;
    float sumSeconds;
    int completed;

    public string LogPath { get { return Path.Combine(Application.persistentDataPath, "trials.csv"); } }
    /// <summary>True while a trial is waiting for Confirm.</summary>
    public bool Running { get { return running; } }
    /// <summary>True from Start until the last trial of the block is confirmed (including the pauses between trials).</summary>
    public bool BlockActive { get { return blockActive; } }
    /// <summary>True after a whole block has been completed.</summary>
    public bool Finished { get { return finished; } }
    public GuideCondition Condition { get { return condition; } }
    /// <summary>1-based number of the current (or just finished) trial.</summary>
    public int TrialNumber { get { return Mathf.Min(index + 1, order.Count); } }
    public int TrialCount { get { return order.Count; } }
    public int Completed { get { return completed; } }
    public float LastAbsError { get { return lastAbsError; } }
    public float LastSeconds { get { return lastSeconds; } }
    public float MeanAbsError { get { return completed > 0 ? sumAbsError / completed : 0f; } }
    public float MeanSeconds { get { return completed > 0 ? sumSeconds / completed : 0f; } }

    /// <summary>For a dropdown listing Visual, Haptic, Both in that order.</summary>
    public void SetCondition(int value)
    {
        condition = (GuideCondition)Mathf.Clamp(value, 0, 2);
        SetStatus("Condition: " + condition);
    }

    public void SetParticipant(string id)
    {
        participantId = string.IsNullOrEmpty(id) ? "P00" : id.Trim();
    }

    /// <summary>Ask the participant to hold their wrist at the start position, then call this.</summary>
    public void ZeroBand()
    {
        if (band != null) band.SendZero();
        SetStatus("Zero set");
    }

    public void StartBlock()
    {
        if (running || blockActive) return;
        order.Clear();
        for (int r = 0; r < repetitions; r++)
            order.AddRange(targets);
        Shuffle(order);
        index = 0;
        completed = 0;
        sumAbsError = 0f;
        sumSeconds = 0f;
        finished = false;
        blockActive = true;
        StartTrial();
    }

    void StartTrial()
    {
        target = order[index];
        startTime = Time.realtimeSinceStartup;
        overshoots = 0;
        lastSign = 0;
        running = true;

        bool showVisual = condition != GuideCondition.Haptic;
        bool useHaptics = condition != GuideCondition.Visual;

        if (targetMarker != null)
        {
            targetMarker.localRotation = Quaternion.Euler(0f, target, 0f);
            targetMarker.gameObject.SetActive(showVisual);
        }
        if (band != null)
            band.SendTarget(target, toleranceDeg, useHaptics);

        SetStatus(string.Format("{0}  trial {1}/{2}", condition, index + 1, order.Count));
    }

    void Update()
    {
        if (!running || rings == null)
            return;

        // Count overshoots: each time the error changes sign, the ring has passed the target.
        float error = Mathf.DeltaAngle(rings.CurrentAngle, target);
        int sign = error > 0f ? 1 : (error < 0f ? -1 : 0);
        if (sign != 0)
        {
            if (lastSign != 0 && sign != lastSign)
                overshoots++;
            lastSign = sign;
        }
    }

    /// <summary>The participant taps this when they believe the ring is aligned.</summary>
    public void Confirm()
    {
        if (!running) return;
        running = false;

        float seconds = Time.realtimeSinceStartup - startTime;
        float finalAngle = rings != null ? rings.CurrentAngle : 0f;
        float error = Mathf.DeltaAngle(finalAngle, target);

        if (band != null) band.SendStop();
        if (targetMarker != null) targetMarker.gameObject.SetActive(false);

        WriteRow(index + 1, finalAngle, error, seconds);
        lastAbsError = Mathf.Abs(error);
        lastSeconds = seconds;
        sumAbsError += lastAbsError;
        sumSeconds += seconds;
        completed++;

        index++;
        if (index < order.Count)
        {
            SetStatus(string.Format("Error {0:F1}°, next trial...", Mathf.Abs(error)));
            StartCoroutine(NextAfterPause());
        }
        else
        {
            blockActive = false;
            finished = true;
            SetStatus("Block finished. Saved to " + LogPath);
        }
    }

    IEnumerator NextAfterPause()
    {
        yield return new WaitForSeconds(pauseBetweenTrials);
        StartTrial();
    }

    void WriteRow(int trialNumber, float finalAngle, float error, float seconds)
    {
        CultureInfo inv = CultureInfo.InvariantCulture;
        bool newFile = !File.Exists(LogPath);
        string row = string.Join(",", new string[] {
            participantId,
            condition.ToString(),
            trialNumber.ToString(inv),
            target.ToString("F1", inv),
            toleranceDeg.ToString("F1", inv),
            finalAngle.ToString("F2", inv),
            error.ToString("F2", inv),
            Mathf.Abs(error).ToString("F2", inv),
            seconds.ToString("F3", inv),
            overshoots.ToString(inv),
            System.DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss", inv)
        });
        try
        {
            if (newFile)
                File.WriteAllText(LogPath,
                    "participant,condition,trial,target_deg,tolerance_deg,final_angle_deg,error_deg,abs_error_deg,time_s,overshoots,timestamp\n");
            File.AppendAllText(LogPath, row + "\n");
        }
        catch (IOException e)
        {
            Debug.LogError("TrialRunner: could not write log: " + e.Message);
        }
    }

    void SetStatus(string text)
    {
        if (statusLabel != null) statusLabel.text = text;
        Debug.Log("TrialRunner: " + text);
    }

    static void Shuffle(List<float> list)
    {
        for (int i = list.Count - 1; i > 0; i--)
        {
            int j = Random.Range(0, i + 1);
            float tmp = list[i];
            list[i] = list[j];
            list[j] = tmp;
        }
    }
}
