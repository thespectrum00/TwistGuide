using UnityEngine;
using UnityEngine.UI;

/// <summary>
/// Guides the user through the app one step at a time and shows only the button that step needs:
///
///   1. Find a table and tap to place the disk
///   2. Wait for the band
///   3. Rest the arm and tap Set zero
///   4. Tap Start
///   5. Each trial: line up, tap Confirm (a short result shows between trials)
///   6. Summary, then Run again
///
/// Put it on the Canvas. It connects the buttons itself, so remove any OnClick entries
/// you added to Zero, Start and Confirm in the Inspector.
/// A "How it works" card opens the first time the app runs and again from the "?" button.
/// </summary>
public class StudyUI : MonoBehaviour
{
    [Header("Links")]
    [SerializeField] TrialRunner runner;
    [SerializeField] BandLink band;
    [SerializeField] PlaceDiskOnTap placer;

    [Header("Text")]
    [Tooltip("The main instruction line. Large and easy to read.")]
    [SerializeField] TMPro.TMP_Text hintLabel;
    [Tooltip("Small connection chip, e.g. top-left: 'Band connected · 12°'.")]
    [SerializeField] TMPro.TMP_Text bandLabel;
    [Tooltip("Optional dot or chip background that turns green when the band is connected.")]
    [SerializeField] Graphic bandDot;
    [SerializeField] Color connectedColor = new Color(0.20f, 0.78f, 0.45f);
    [SerializeField] Color missingColor = new Color(0.90f, 0.35f, 0.30f);
    [SerializeField] bool showAngle = true;

    [Header("Buttons")]
    [SerializeField] Button zeroButton;
    [SerializeField] Button startButton;
    [SerializeField] Button confirmButton;
    [Tooltip("Small '?' button that reopens the How it works card.")]
    [SerializeField] Button helpButton;

    [Header("First-time info card")]
    [SerializeField] GameObject infoPanel;
    [SerializeField] Button infoCloseButton;
    [Tooltip("Optional: if set, the text below is written into it. Leave empty to type the text in the card yourself.")]
    [SerializeField] TMPro.TMP_Text infoBody;
    [TextArea(8, 16)]
    [SerializeField] string infoText =
        "<b>How it works</b>\n\n" +
        "1.  Put on the band and turn on your phone's hotspot.\n" +
        "2.  Point the phone at a table and move it slowly. When a grid appears, tap it to place the disk.\n" +
        "3.  Rest your forearm on the table, palm down and relaxed, then tap <b>Set zero</b>.\n" +
        "4.  Tap <b>Start</b>. Twist your wrist to turn the <color=#E5484D>red notch</color> onto the <color=#30A46C>green needle</color>, then tap <b>Confirm</b>.\n\n" +
        "Each round has several targets. Be quick, but be accurate.";

    const string SeenIntroKey = "seenIntro";
    bool zeroed;
    TMPro.TMP_Text startButtonText;

    void Start()
    {
        if (zeroButton != null) zeroButton.onClick.AddListener(OnZero);
        if (startButton != null)
        {
            startButton.onClick.AddListener(OnStart);
            startButtonText = startButton.GetComponentInChildren<TMPro.TMP_Text>(true);
        }
        if (confirmButton != null) confirmButton.onClick.AddListener(OnConfirm);
        if (helpButton != null) helpButton.onClick.AddListener(ShowInfo);
        if (infoCloseButton != null) infoCloseButton.onClick.AddListener(HideInfo);

        if (infoBody != null && !string.IsNullOrEmpty(infoText))
            infoBody.text = infoText;

        bool seen = false;
        try { seen = PlayerPrefs.GetInt(SeenIntroKey, 0) == 1; } catch (System.Exception) { }
        if (infoPanel != null) infoPanel.SetActive(!seen);
    }

    void OnZero()
    {
        if (runner != null) runner.ZeroBand();
        zeroed = true;
    }

    void OnStart()
    {
        if (runner != null) runner.StartBlock();
    }

    void OnConfirm()
    {
        if (runner != null) runner.Confirm();
    }

    public void ShowInfo()
    {
        if (infoPanel != null) infoPanel.SetActive(true);
    }

    public void HideInfo()
    {
        if (infoPanel != null) infoPanel.SetActive(false);
        try { PlayerPrefs.SetInt(SeenIntroKey, 1); PlayerPrefs.Save(); } catch (System.Exception) { }
    }

    void Update()
    {
        bool connected = band != null && band.Connected;
        bool placed = placer == null || placer.Placed;
        bool inBlock = runner != null && runner.BlockActive;
        bool inTrial = runner != null && runner.Running;
        bool finished = runner != null && runner.Finished;

        UpdateBandChip(connected);

        // Which buttons this step needs. Hidden buttons can't be pressed by mistake.
        SetShown(zeroButton, placed && !inBlock, connected);
        SetShown(startButton, placed && zeroed && !inBlock, connected);
        SetShown(confirmButton, inTrial, true);
        if (startButtonText != null)
            startButtonText.text = finished ? "Run again" : "Start";

        if (hintLabel != null)
            hintLabel.text = Hint(connected, placed, inBlock, inTrial, finished);
    }

    string Hint(bool connected, bool placed, bool inBlock, bool inTrial, bool finished)
    {
        if (!placed)
            return "Point your phone at a table and move it slowly.\nWhen a grid appears, tap it to place the disk.";
        if (!connected && !inBlock)
            return "Looking for the band...\nCheck it's switched on and your hotspot is on.";
        if (!zeroed)
            return "Rest your forearm on the table, palm down and relaxed.\nThen tap Set zero.";
        if (inTrial)
        {
            string how = runner.Condition == GuideCondition.Haptic
                ? "Follow the buzz around your wrist until you feel the click."
                : "Turn the red notch onto the green needle.";
            return string.Format("Target {0} of {1}\n{2} Then tap Confirm.", runner.TrialNumber, runner.TrialCount, how);
        }
        if (inBlock)
            return string.Format("Off by {0:F1}° in {1:F1} s\nNext target coming...", runner.LastAbsError, runner.LastSeconds);
        if (finished)
            return string.Format("Done! {0} targets\nAverage error {1:F1}°   ·   Average time {2:F1} s",
                runner.Completed, runner.MeanAbsError, runner.MeanSeconds);
        return "Ready. Tap Start, then turn the red notch onto the green needle\nand tap Confirm for each target.";
    }

    void UpdateBandChip(bool connected)
    {
        if (bandLabel != null)
        {
            if (!connected)
                bandLabel.text = "Band not connected";
            else if (showAngle)
                bandLabel.text = string.Format("Band connected · {0:F0}°", band.Angle);
            else
                bandLabel.text = "Band connected";
        }
        if (bandDot != null)
            bandDot.color = connected ? connectedColor : missingColor;
    }

    static void SetShown(Button button, bool shown, bool interactable)
    {
        if (button == null) return;
        if (button.gameObject.activeSelf != shown)
            button.gameObject.SetActive(shown);
        button.interactable = interactable;
    }
}
