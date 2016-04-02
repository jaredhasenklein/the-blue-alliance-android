package com.thebluealliance.androidclient.fragments.gameday;

import com.thebluealliance.androidclient.IntegrationRobolectricRunner;
import com.thebluealliance.androidclient.fragments.framework.FragmentTestDriver;

import org.junit.Before;
import org.junit.Test;
import org.junit.runner.RunWith;

@RunWith(IntegrationRobolectricRunner.class)
public class GamedayWebcastsFragmentTest {

    GamedayWebcastsFragment mFragment;

    @Before
    public void setUp() {
        mFragment = GamedayWebcastsFragment.newInstance();
    }

    @Test
    public void testLifecycle() {
        FragmentTestDriver.testLifecycle(mFragment);
    }
}