'use client';
import Image from 'next/image';
import { useRef, useState, useEffect } from 'react';
import { fetch_data } from './api';
import Readout from './readout';
import HealthPanel from './health_panel';
import VecReadout from './vec_readout';
import STLModel from './stl_model';

export default function Home() {
    const [state, updateState] = useState({
        altitude_bmp: 0,
        altitude_tof: 0,
        gyro_lsm: [0, 0, 0],
        accel_lsm: [0, 0, 0],
        mag_lis: [0, 0, 0],
        gyro_bno: [0, 0, 0],
        lat_cd: 0.0,
        lon_cd: 0.0,
        lat_rtk: 0.0,
        lon_rtk: 0.0,

        //  lpf outputs
        bmp_lpf: 0.0,
        gyro_lpf: [0, 0, 0],
        attitude_lpf: [0, 0, 0, 0],

        // controls outputs (phase 1)
        thrust: 0.0,
        moment: 0.0,
        beta_y_deg: 0.0,
        beta_z_deg: 0.0,

        // controls outputs (phase 2)
        props_top_pwm: 0,
        props_btm_pwm: 0,
        tvc_y_deg: 0,
        tvc_z_deg: 0,

        temperature: 0.0,
        esc_voltage: 0.0,
        servo_voltage: 0.0,
        connected: false,
        connection_reliability: 0.0,
        health: [
            ['GPS', false],
            ['RTK', false],
            ['BMP', false],
            ['TOF', false],
            ['LSM', false],
            ['LIS', false],
            ['BNO', false],
            ['AUX', false],
        ],
    });

    useEffect(() => {
        const interval = setInterval(() => {
            fetch_data()
                .then((data) => {
                    if (!data) return;
                    updateState(data);
                })
                .catch((err) => console.log(err));
        }, 100);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className='bg-black h-screen text-white font-sans overflow-hidden'>
            {/* HEADER */}
            <header>
                <div className='flex items-center p-4 space-x-4'>
                    <div className='logo'>
                        <Image
                            src='/rocketteam.png'
                            alt='MIT Rocket Team'
                            width={100}
                            height={50}
                            className='inline-block'
                        />
                    </div>
                    <div className='text-2xl tracking-widest'>SPHINX</div>
                    <div className='text-2xl tracking-widest text-gray-400'>〉TELEMETRY</div>
                    <div className='flex-1'></div>
                    {state.connected ? (
                        <div className='text-green-500 font-mono tracking-widest border border-green-900 rounded-full px-2'>
                            ● {Math.round(state.connection_reliability * 100)}% PACKETS RECEIVED
                        </div>
                    ) : (
                        <div className='text-red-500 font-mono tracking-widest border border-red-900 rounded-full px-2'>
                            ● DISCONNECTED
                        </div>
                    )}
                    <Image src='/mit.png' alt='MIT Logo' width={60} height={20} className='inline-block' />
                </div>
                <div className='border-t h-0.5 border-gray-400 mx-4'></div>
            </header>
            {/* MAIN CONTENT */}
            <main className='p-4 space-y-6'>
                <div className='grid grid-cols-[2fr_3fr] gap-4'>
                    <div className=''>
                        <div className='text-gray-400 uppercase tracking-widest text-center mb-2'>Vehicle View</div>
                        <STLModel
                            url='/sphinx.stl'
                            rotation={
                                //[0, Math.PI / 8, 0]
                                [((270 - state.gyro_bno[1]) * Math.PI) / 180, (state.gyro_bno[2] * Math.PI) / 180, 0]
                            }
                            scale={0.3}
                            color='#ff5e66'
                        />
                        {/* <div className="text-gray-400 uppercase tracking-widest text-center mt-4 mb-2">Human Input</div>
          <div className="grid grid-cols-3 gap-5">
            <Image src="/launch.png" width={700} height={700} alt="Launch Command" className="rounded-2xl"/>
            <Image src="/land.png" width={700} height={700} alt="Land Command" className="rounded-2xl"/>
            <Image src="/abort.png" width={700} height={700} alt="Abort Command" className="rounded-2xl"/>
          </div> */}
                        <div className='text-gray-400 uppercase tracking-widest text-center my-2'>Control Output</div>
                        <div className='grid grid-cols-3 gap-2'>
                            <Readout label='Thrust' value={state.thrust} unit=' N' />
                            <Readout label='w_top' value={state.props_top_pwm} unit=' rad/s' capitalize={false} />
                            <Readout label='w_bot' value={state.props_btm_pwm} unit=' rad/s' capitalize={false} />
                            <Readout label='Moment' value={state.moment} unit=' mNm' />
                            <Readout label='β_y' value={state.beta_y_deg} unit='°' capitalize={false} />
                            <Readout label='β_z' value={state.beta_z_deg} unit='°' capitalize={false} />
                        </div>
                    </div>
                    <div className=''>
                        <div className='text-gray-400 uppercase tracking-widest text-center mb-2'>Health</div>
                        <HealthPanel objects={state.health as [string, boolean][]} />
                        <div className='text-gray-400 uppercase tracking-widest text-center my-2'>State Estimation</div>
                        <div className='grid grid-cols-3 gap-2'>
                            <VecReadout
                                label='Position (m)'
                                values={[
                                    ['x', state.bmp_lpf],
                                    ['y', 0],
                                    ['z', 0],
                                ]}
                            />
                            <VecReadout
                                label='Velocity (mm/s)'
                                values={[
                                    ['x', 0],
                                    ['y', 0],
                                    ['z', 0],
                                ]}
                            />
                            <VecReadout
                                label='Quaternion'
                                values={[
                                    ['w', state.attitude_lpf[0]],
                                    ['x', state.attitude_lpf[1]],
                                    ['y', state.attitude_lpf[2]],
                                    ['z', state.attitude_lpf[3]],
                                ]}
                            />
                        </div>
                        <div className='text-gray-400 uppercase tracking-widest text-center my-2'>Readouts</div>
                        <div className='grid grid-cols-4 gap-2'>
                            <Readout label='Altitude/BMP' value={state.altitude_bmp} unit=' m' mini={true} />
                            <Readout label='Altitude/ToF' value={state.altitude_tof} unit=' m' mini={true} />
                            <Readout label='Gyro[X]/LSM' value={state.gyro_lsm[0]} unit=' m°/s' mini={true} />
                            <Readout label='Gyro[Y]/LSM' value={state.gyro_lsm[1]} unit=' m°/s' mini={true} />
                            <Readout label='Gyro[Z]/LSM' value={state.gyro_lsm[2]} unit=' m°/s' mini={true} />
                            <Readout label='Accel[X]/LSM' value={state.accel_lsm[0]} unit=' mg' mini={true} />
                            <Readout label='Accel[Y]/LSM' value={state.accel_lsm[1]} unit=' mg' mini={true} />
                            <Readout label='Accel[Z]/LSM' value={state.accel_lsm[2]} unit=' mg' mini={true} />
                            <Readout label='Heading/BNO' value={state.gyro_bno[0]} unit='°' mini={true} />
                            <Readout label='Roll/BNO' value={state.gyro_bno[1]} unit='°' mini={true} />
                            <Readout label='Pitch/BNO' value={state.gyro_bno[2]} unit='°' mini={true} />
                            <Readout label='Lat/CD' value={state.lat_cd} unit='°' mini={true} />
                            <Readout label='Lon/CD' value={state.lon_cd} unit='°' mini={true} />
                            <Readout label='Lat/RTK' value={state.lat_rtk} unit='°' mini={true} />
                            <Readout label='Lon/RTK' value={state.lon_rtk} unit='°' mini={true} />
                            <Readout label='Temperature' value={state.temperature} unit=' °C' mini={true} />
                            <Readout label='Batt Voltage' value={state.esc_voltage} unit=' V' mini={true} />
                            <Readout label='Servo Voltage' value={state.servo_voltage} unit=' V' mini={true} />
                        </div>
                    </div>
                </div>
            </main>
        </div>
    );
}
