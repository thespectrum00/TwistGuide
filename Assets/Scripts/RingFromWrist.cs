using UnityEngine;

/// <summary>
/// Makes the selected ring follow the wrist. Put it on the same "Band" object as BandLink.
/// While the band is connected it overrides the slider; when the band goes quiet the slider works again.
///
/// If the ring turns the opposite way to your wrist, fix it on the band (TWIST_SIGN in config.py),
/// not here, so the phone and the band always agree on which way is positive.
/// </summary>
public class RingFromWrist : MonoBehaviour
{
    [SerializeField] BandLink band;
    [SerializeField] RingController rings;

    [Tooltip("Optional text that shows whether the band is connected and its current angle.")]
    [SerializeField] TMPro.TMP_Text statusLabel;

    void Update()
    {
        if (band == null || rings == null)
            return;

        if (band.Connected)
            rings.SetAngle(band.Angle);

        if (statusLabel != null)
        {
            statusLabel.text = band.Connected
                ? string.Format("Band {0}   {1:F1}°", band.BandAddress, band.Angle)
                : "Band not connected";
        }
    }
}
