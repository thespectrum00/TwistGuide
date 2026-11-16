using UnityEngine;

/// <summary>
/// Stands the disk up so it faces you like a clock, instead of lying flat on the table.
/// Put it on the Disk, next to RingController. 0° (the needle and the red notch at rest) points to 12 o'clock.
///
/// Facing modes:
///   FaceScreen   - the clock face always stays parallel to the phone screen, 12 o'clock at the top of the screen.
///   UprightOnce  - stands upright facing where you were when you placed it, then stays put like a desk clock.
///   FlatOnTable  - the original behaviour: lying on the table.
///
/// A clockwise wrist twist still turns the ring clockwise as you see it.
/// </summary>
public class DiskFacing : MonoBehaviour
{
    public enum Mode { FaceScreen, UprightOnce, FlatOnTable }

    [SerializeField] Mode mode = Mode.FaceScreen;

    [Tooltip("How far above the tapped point the centre of the clock sits, in metres. 0.12 lets a 20 cm disk clear the table.")]
    [SerializeField] float liftAboveTable = 0.12f;

    [Tooltip("The AR camera. Leave empty to use the camera tagged MainCamera.")]
    [SerializeField] Camera arCamera;

    Vector3 anchor;

    void OnEnable()
    {
        // PlaceDiskOnTap moves the disk to the tapped point just before switching it on.
        anchor = transform.position;
        if (mode != Mode.FlatOnTable)
            transform.position = anchor + Vector3.up * liftAboveTable;
        Orient();
    }

    void LateUpdate()
    {
        if (mode == Mode.FaceScreen)
            Orient();
    }

    void Orient()
    {
        Camera cam = arCamera != null ? arCamera : Camera.main;
        if (cam == null || mode == Mode.FlatOnTable)
            return;

        Transform c = cam.transform;
        Vector3 toCamera = c.position - transform.position;
        if (toCamera.sqrMagnitude < 1e-6f)
            return;

        if (mode == Mode.FaceScreen)
        {
            // Face axis (local up, the axis the rings turn about) points back at the screen;
            // local forward (0°, 12 o'clock) points to the top of the screen.
            transform.rotation = Quaternion.LookRotation(c.up, -c.forward);
        }
        else
        {
            // Upright: face the camera horizontally, 12 o'clock pointing straight up.
            Vector3 flat = new Vector3(toCamera.x, 0f, toCamera.z);
            if (flat.sqrMagnitude < 1e-6f)
                flat = -c.forward;
            transform.rotation = Quaternion.LookRotation(Vector3.up, flat.normalized);
        }
    }
}
